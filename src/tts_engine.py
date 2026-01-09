import os
import torch
import scipy.io.wavfile
import numpy as np
import asyncio
import edge_tts
import io
from pydub import AudioSegment
from transformers import VitsModel, AutoTokenizer

# TTS Provider Metadata
TTS_PROVIDERS = {
    'mms': {
        'name': 'HuggingFace MMS',
        'quality': '⭐⭐⭐ Good',
        'speed': '🐢 Slow (CPU)',
        'size': '~400MB',
        'type': 'Offline'
    },
    'edge': {
        'name': 'Microsoft Edge',
        'quality': '⭐⭐⭐⭐⭐ Excellent',
        'speed': '⚡ Very Fast',
        'size': '0MB (Online)',
        'type': 'Online'
    },
    'gtts': {
        'name': 'Google TTS',
        'quality': '⭐⭐⭐ Good',
        'speed': '⚡ Fast',
        'size': '0MB (Online)',
        'type': 'Online'
    },
    'silero': {
        'name': 'Silero TTS',
        'quality': '⭐⭐⭐⭐ Very Good',
        'speed': '🐢 Medium',
        'size': '~100MB',
        'type': 'Offline'
    }
}

class TTSEngine:
    def __init__(self, provider="mms", voice=None, lang="ar", device=None):
        self.provider = provider
        self.lang = lang
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.sampling_rate = 16000 # Default fallback
        
        # Default voices based on language and provider
        if not voice:
            if provider == "mms":
                voice = "facebook/mms-tts-ara" if lang == "ar" else "facebook/mms-tts-eng"
            elif provider == "edge":
                voice = "ar-EG-SalmaNeural" if lang == "ar" else "en-US-AndrewNeural"
            elif provider == "gtts":
                voice = "ar" if lang == "ar" else "en"
            elif provider == "silero":
                voice = "xglm_v1" # Silero Arabic
                if lang != "ar":
                    print(f"Warning: Silero is currently only configured for Arabic in this tool.")
        
        self.voice = voice
        
        if self.provider == "mms":
            print(f"Loading HF model {self.voice} on {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.voice)
            self.model = VitsModel.from_pretrained(self.voice).to(self.device)
            self.sampling_rate = self.model.config.sampling_rate
        elif self.provider == "edge":
            print(f"Initialized Edge TTS with voice: {self.voice}")
            self.sampling_rate = 24000
        elif self.provider == "gtts":
            print(f"Initialized Google TTS (lang: {self.lang})")
            self.sampling_rate = 24000
        elif self.provider == "silero":
            print(f"Initializing Silero TTS (model loads on first use)...")
            self.sampling_rate = 48000
    
    def synthesize_text(self, text):
        if self.provider == "mms":
            return self._synthesize_mms(text)
        elif self.provider == "edge":
            return self._synthesize_edge(text)
        elif self.provider == "gtts":
            return self._synthesize_gtts(text)
        elif self.provider == "silero":
            return self._synthesize_silero(text)
            
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

    def _synthesize_gtts(self, text):
        """Synthesize using Google Text-to-Speech"""
        from gtts import gTTS
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            temp_path = f.name
        
        try:
            tts = gTTS(text=text, lang=self.lang, slow=False)
            tts.save(temp_path)
            
            # Convert MP3 to numpy array
            audio = AudioSegment.from_mp3(temp_path)
            self.sampling_rate = audio.frame_rate
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples = samples / 32768.0  # Normalize to [-1, 1]
            
            return samples
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _synthesize_silero(self, text):
        """Synthesize using Silero TTS"""
        # Lazy load model on first use
        if not hasattr(self, 'silero_model'):
            print("  Downloading Silero model (first time only, ~100MB)...")
            self.silero_model, _, self.silero_sample_rate, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-models',
                model='silero_tts',
                language='ar',
                speaker='xglm_v1'
            )
            self.sampling_rate = self.silero_sample_rate
            self.silero_model.to(self.device)
        
        # Generate audio
        audio = self.silero_model.apply_tts(
            text=text,
            speaker='xglm_v1',
            sample_rate=self.sampling_rate
        )
        
        return audio.cpu().numpy()

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
