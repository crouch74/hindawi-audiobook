import os
import torch
import scipy.io.wavfile
import numpy as np
from transformers import VitsModel, AutoTokenizer

class TTSEngine:
    MODEL_NAME = "facebook/mms-tts-ara"

    def __init__(self, device=None):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        print(f"Loading TTS model {self.MODEL_NAME} on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.model = VitsModel.from_pretrained(self.MODEL_NAME).to(self.device)
        self.sampling_rate = self.model.config.sampling_rate

    def synthesize_text(self, text):
        inputs = self.tokenizer(text, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            output = self.model(**inputs).waveform
        
        # Output is (batch, channels, time) -> (1, 1, T) usually
        # We need numpy array (T,)
        waveform = output.cpu().numpy()[0, 0, :]
        return waveform

    def chunk_text(self, text, max_chars=400):
        """
        Splits text into chunks to avoid TTS breakdown on long sequences.
        Splits by sentence boundaries.
        """
        # Simple splitting by punctuation
        # Arabic punctuation: . ? ! resulting in split
        # We can normalize slightly
        import re
        # Split by common ending punctuation
        sentences = re.split(r'([.?!؟]+)', text)
        
        chunks = []
        current_chunk = ""
        
        for part in sentences:
            # part could be the sentence or the punctuation
            if not part.strip():
                continue
                
            # If adding this part exceeds max, push current chunk
            if len(current_chunk) + len(part) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
            
            current_chunk += part
            
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    def synthesize_chapter(self, text, output_file):
        """
        Synthesizes full chapter text to a WAV file.
        """
        if os.path.exists(output_file):
            print(f"File {output_file} exists. Skipping TTS.")
            return

        chunks = self.chunk_text(text)
        print(f"Synthesizing {len(chunks)} chunks to {output_file}...")
        
        audio_segments = []
        # Add a small silence between chunks (e.g., 0.5s)
        # 0.5 * rate
        silence_len = int(0.5 * self.sampling_rate)
        silence = np.zeros(silence_len, dtype=np.float32)

        for i, chunk in enumerate(chunks):
            if not chunk.strip(): 
                continue
            try:
                wav = self.synthesize_text(chunk)
                audio_segments.append(wav)
                audio_segments.append(silence)
            except Exception as e:
                print(f"Error synthesizing chunk {i}: {e}")
                # Skip bad chunks or retry? minimal skip for now.

        if not audio_segments:
            print("No audio generated for chapter.")
            return

        full_audio = np.concatenate(audio_segments)
        
        # Save
        # normalize float audio to int16 for compatibility if needed, or keep float
        # standard wavfile handles float32 [-1, 1] usually.
        scipy.io.wavfile.write(output_file, self.sampling_rate, full_audio)
