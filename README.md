# Hindawi Audiobook CLI

Convert public-domain Arabic books from Hindawi.org into fully chaptered M4B audiobooks with optional PDF appendices.

## Features

- 📚 **Scrape** book content from Hindawi.org
- 🎵 **Smart Audio Detection**: Automatically downloads pre-recorded audio when available
- 🎙️ **Multiple TTS Options**: 
  - **Online**: 
    - **Microsoft Edge TTS**: Best quality, multiple voices, very fast (0MB)
    - **Google TTS (gTTS)**: Reliable, standard quality, fast (0MB)
  - **Offline**:
    - **HuggingFace MMS**: Good quality, slow (CPU only), (~400MB)
    - **Silero TTS**: Very good quality, natural sounding, medium speed (~100MB)
- 🎧 **M4B Audiobooks** with chapters, metadata, and cover art
- 📄 **PDF Appendices** containing images, captions, and footnotes
- 🐳 **Docker Support** for easy deployment
- 🎨 **Rich CLI** with progress bars and detailed logging

## TTS Provider Comparison

| Provider | Type | Quality | Speed | Download Size | Best For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Edge TTS** | Online | ⭐⭐⭐⭐⭐ | ⚡ Fast | 0MB | High quality online |
| **Google TTS** | Online | ⭐⭐⭐ | ⚡ Fast | 0MB | Lightweight online |
| **Silero TTS** | Offline | ⭐⭐⭐⭐ | 🐢 Medium | ~100MB | High quality offline |
| **HF MMS** | Offline | ⭐⭐⭐ | 🐢 Slow | ~400MB | Standard offline |

---

## Installation

### Local Installation

```bash
# Clone the repository
git clone <repository-url>
cd hindawi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Docker Installation

```bash
# Build the Docker image
docker build -t hindawi_audiobook .
```

## Usage

### Local Usage (Interactive)

```bash
# Interactive mode - prompts for all options
python -m src.main 46319638
```

### Local Usage (Non-Interactive)

```bash
# Generate both audio and PDF
python -m src.main 46319638 --mode both --tts-provider edge --voice ar-EG-SalmaNeural

# Generate audio only with MMS
python -m src.main 46319638 --mode audio --tts-provider mms

# Generate PDF appendix only
python -m src.main 46319638 --mode pdf
```

### Docker Usage

```bash
# PDF only (no TTS needed, works in Docker)
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/cache:/app/cache \
  hindawi_audiobook 46319638 --mode pdf

# Audio with Edge TTS (requires internet)
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/cache:/app/cache \
  hindawi_audiobook 46319638 --mode audio --tts-provider edge --voice ar-EG-SalmaNeural

# Both audio and PDF
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/cache:/app/cache \
  hindawi_audiobook 46319638 --mode both --tts-provider edge --voice ar-EG-SalmaNeural
```

## Command-Line Options

```
positional arguments:
  book_id               The ID of the book on Hindawi.org (e.g., 46319638)

optional arguments:
  --output-dir DIR      Directory to save final outputs (default: output)
  --cache-dir DIR       Directory for intermediate files (default: cache)
  --mode {audio,pdf,both}
                        Generation mode (default: interactive prompt)
  --tts-provider {edge,gtts,silero,mms}
                        TTS provider (default: interactive prompt)
  --voice VOICE         Voice for Edge TTS (default: ar-EG-SalmaNeural)
```

## Available Voices

### Microsoft Edge (Online)
- **Egyptian**: `ar-EG-SalmaNeural` (F), `ar-EG-ShakirNeural` (M)
- **Saudi**: `ar-SA-HamedNeural` (M), `ar-SA-ZariyahNeural` (F)

### Other Providers
- **Google TTS**: Automatic Arabic (`ar`)
- **Silero**: High-quality Arabic speaker (`xglm_v1`)
- **HF MMS**: Standard Arabic model

## Usage Examples

### Example 1: High Quality Online (Edge)
```bash
python -m src.main 46319638 --mode audio --tts-provider edge --voice ar-EG-SalmaNeural
```

### Example 2: High Quality Offline (Silero)
```bash
python -m src.main 46319638 --mode audio --tts-provider silero
```

### Example 3: Quick PDF Only
```bash
python -m src.main 46319638 --mode pdf
```

## Troubleshooting

### Docker 403 Errors
The Hindawi website may block requests from Docker containers. If you encounter 403 errors:
1. Use `--mode pdf` which works reliably in Docker
2. For audio generation, run locally instead of in Docker
3. Consider using a proxy if Docker audio generation is required

### Missing Dependencies
If you encounter missing system dependencies, ensure you have:
- `ffmpeg` for audio processing
- `cairo`, `pango` for PDF generation
- `nodejs` for cloudscraper

## License

This tool is for educational purposes. Respect Hindawi's terms of service and only use with public-domain content.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
