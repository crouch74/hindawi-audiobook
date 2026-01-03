import os
import torch
import scipy.io.wavfile
import numpy as np
import asyncio
import edge_tts
import io
from pydub import AudioSegment
from transformers import VitsModel, AutoTokenizer

class TTSEngine:
    def __init__(self, provider="mms", voice="facebook/mms-tts-ara", device=None):
        self.provider = provider
        self.voice = voice # Model name or Edge voice name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.sampling_rate = 16000 # Default fallback
        
        if self.provider == "mms":
            print(f"Loading HF model {self.voice} on {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.voice)
            self.model = VitsModel.from_pretrained(self.voice).to(self.device)
            self.sampling_rate = self.model.config.sampling_rate
        elif self.provider == "edge":
            print(f"Initialized Edge TTS with voice: {self.voice}")
            # Edge rate is dynamic, but usually 24k/48k. We'll set it after first synth or assume 24k.
            self.sampling_rate = 24000 
    
    def synthesize_text(self, text):
        if self.provider == "mms":
            return self._synthesize_mms(text)
        elif self.provider == "edge":
            return self._synthesize_edge(text)
            
    def _synthesize_mms(self, text):
        inputs = self.tokenizer(text, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            output = self.model(**inputs).waveform
        wav = output.cpu().numpy()
        if wav.ndim == 3: waveform = wav[0, 0, :]
        elif wav.ndim == 2: waveform = wav[0, :]
        else: waveform = wav.flatten()
        return waveform

    def _synthesize_edge(self, text):
        # run async in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        audio_bytes = loop.run_until_complete(self._edge_gen(text))
        
        # Convert mp3 bytes to numpy
        audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        self.sampling_rate = audio.frame_rate
        
        # pydub to numpy
        # data is int16 usually. Flatten channels if stereo.
        if audio.channels > 1:
            audio = audio.set_channels(1)
            
        arr = np.array(audio.get_array_of_samples())
        
        # normalize to float32 [-1, 1]
        arr = arr.astype(np.float32) / 32768.0
        return arr

    async def _edge_gen(self, text):
        communicate = edge_tts.Communicate(text, self.voice)
        data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                data += chunk["data"]
        return data

    def chunk_text(self, text, max_chars=400):
        """
        Splits text into chunks to avoid TTS breakdown on long sequences.
        Splits by sentence boundaries.
        """
        import re
        sentences = re.split(r'([.?!؟]+)', text)
        chunks = []
        current_chunk = ""
        for part in sentences:
            if not part.strip():
                continue
            if len(current_chunk) + len(part) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
            current_chunk += part
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def get_silence(self, duration_sec=0.5):
        silence_len = int(duration_sec * self.sampling_rate)
        return np.zeros(silence_len, dtype=np.float32)

    def save_to_file(self, segments, output_file):
        if not segments:
            print("No audio segments to save.")
            return

        full_audio = np.concatenate(segments)
        scipy.io.wavfile.write(output_file, self.sampling_rate, full_audio)
