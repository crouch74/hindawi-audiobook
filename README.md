# Hindawi Audiobook CLI

Convert public-domain Arabic books from Hindawi.org into fully chaptered M4B audiobooks with optional PDF appendices.

## Features

- 📚 **Scrape** book content from Hindawi.org
- 🎵 **Smart Audio Detection**: Automatically downloads pre-recorded audio when available
- 🎙️ **Multiple TTS Options**: 
  - Offline: HuggingFace MMS (facebook/mms-tts-ara)
  - Online: Microsoft Edge TTS with multiple Arabic voices
- 🎧 **M4B Audiobooks** with chapters, metadata, and cover art
- 📄 **PDF Appendices** containing images, captions, and footnotes
- 🐳 **Docker Support** for easy deployment
- 🎨 **Rich CLI** with progress bars and detailed logging

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
  --tts-provider {mms,edge}
                        TTS provider (default: interactive prompt)
  --voice VOICE         Voice for Edge TTS:
                        - ar-EG-SalmaNeural (Egypt - Female)
                        - ar-EG-ShakirNeural (Egypt - Male)
                        - ar-SA-HamedNeural (Saudi Arabia - Male)
                        - ar-SA-ZariyahNeural (Saudi Arabia - Female)
```

## Available Voices

### Egyptian Arabic
- **Salma** (Female): `ar-EG-SalmaNeural`
- **Shakir** (Male): `ar-EG-ShakirNeural`

### Saudi Arabic
- **Hamed** (Male): `ar-SA-HamedNeural`
- **Zariyah** (Female): `ar-SA-ZariyahNeural`

## Output Files

- **M4B Audiobook**: `output/<book_title>.m4b`
- **PDF Appendix**: `output/<book_title>_Appendix.pdf`
- **Cache Files**: `cache/<book_id>/` (WAV files, metadata, cover)

## Examples

### Example 1: Quick PDF Generation
```bash
docker run --rm -v $(pwd)/output:/app/output -v $(pwd)/cache:/app/cache \
  hindawi_audiobook 46319638 --mode pdf
```

### Example 2: Full Audiobook with Egyptian Female Voice
```bash
python -m src.main 46319638 \
  --mode both \
  --tts-provider edge \
  --voice ar-EG-SalmaNeural
```

### Example 3: Offline Audio Generation
```bash
python -m src.main 46319638 \
  --mode audio \
  --tts-provider mms
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
