# Hindawi Audiobook CLI

A command-line tool to convert public domain Arabic books from [Hindawi.org](https://www.hindawi.org) into high-quality M4B audiobooks. It uses Neural TTS (Facebook MMS-TTS) for natural Arabic speech and proper chapter support.

## Features

-   **Scrapes Hindawi Books**: Fetches text, metadata (title, author), and cover art automatically.
-   **Neural TTS**: Uses `facebook/mms-tts-ara` for natural Arabic narration (VITS model).
-   **Full Audiobook Format**: Produces a single `.m4b` file with:
    -   Chapter markers (mapped to book TOC).
    -   Embedded cover art.
    -   Correct metadata.
-   **Resume Capability**: Caches generated audio chapters to allow resuming if interrupted.
-   **Dockerized**: Easy to run without dependency hell.

## Prerequisites

-   Docker
-   Internet connection (for initial model download and scraping)

## Quick Start

### 1. Build the Docker Image

```bash
docker build -t hindawi_audiobook .
```

### 2. Run the Tool

Use the book ID from the Hindawi URL (e.g., for `https://www.hindawi.org/books/46319638/`, the ID is `46319638`).

Create necessary directories for output and cache:

```bash
mkdir -p output cache
```

Run the container:

```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/cache:/app/cache \
  hindawi_audiobook <BOOK_ID>
```

**Example:**

```bash
docker run --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/cache:/app/cache \
  hindawi_audiobook 46319638
```

### 3. Check Output

The requested book will be saved as an `.m4b` file in the `output/` directory.

## Configuration

-   **Cache**: The `cache/` directory stores downloaded intermediate WAV files and cover images. If the process is stopped, running it again will reuse these files.
-   **Performance**: TTS generation is CPU intensive. On a standard CPU, it may take 1-2x real-time to generate audio (i.e., a 5-hour book might take 5-10 hours).

## Development

The source code is located in `src/`:
-   `src/main.py`: CLI entry point.
-   `src/scraper.py`: Hindawi scraping logic.
-   `src/tts_engine.py`: TTS model interface.
-   `src/audiobook_builder.py`: Audio assembly and M4B muxing.

To run locally without Docker (requires ffmpeg, python 3.10+):

```bash
pip install -r requirements.txt
python -m src.main <BOOK_ID>
```

## License

This tool is for educational purposes. Please ensure you comply with Hindawi's terms of service and copyright laws regarding the texts.
