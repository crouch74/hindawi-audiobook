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
        wav = output.cpu().numpy()
        # Handle shape (batch, channels, time) or (batch, time)
        if wav.ndim == 3:
             waveform = wav[0, 0, :]
        elif wav.ndim == 2:
             waveform = wav[0, :]
        else:
             waveform = wav.flatten()
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

    def get_silence(self, duration_sec=0.5):
        silence_len = int(duration_sec * self.sampling_rate)
        return np.zeros(silence_len, dtype=np.float32)

    def save_to_file(self, segments, output_file):
        if not segments:
            print("No audio segments to save.")
            return

        full_audio = np.concatenate(segments)
        scipy.io.wavfile.write(output_file, self.sampling_rate, full_audio)
