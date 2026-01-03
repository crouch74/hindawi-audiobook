import argparse
import os
import sys
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from .scraper import Scraper
from .tts_engine import TTSEngine
from .audiobook_builder import AudiobookBuilder
from .logger import console, log_info, log_success, log_error, log_warning

def main():
    parser = argparse.ArgumentParser(description="Convert Hindawi books to M4B audiobook.")
    parser.add_argument('book_id', help="The ID of the book on Hindawi.org (e.g., 46319638)")
    parser.add_argument('--output-dir', default='output', help="Directory to save the final M4B")
    parser.add_argument('--cache-dir', default='cache', help="Directory for intermediate files")
    
    args = parser.parse_args()
    
    book_id = args.book_id
    output_dir = args.output_dir
    cache_dir = os.path.join(args.cache_dir, book_id)
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)
    
    log_info(f"🚀  Starting Audiobook Generation for Book ID: {book_id}")
    
    # 1. Scrape Metadata
    scraper = Scraper(book_id)
    try:
        with console.status("[bold green]Fetching metadata...", spinner="dots"):
            metadata = scraper.get_book_metadata()
    except Exception as e:
        log_error(f"❌  Error fetching metadata: {e}")
        sys.exit(1)
        
    log_info(f"📖  Title: {metadata['title']}")
    log_info(f"✍️  Author: {metadata['author']}")
    log_info(f"📑  Found {len(metadata['chapters'])} chapters.")
    
    # 2. Download Cover
    cover_path = os.path.join(cache_dir, "cover.png")
    if metadata['cover_url']:
        if not os.path.exists(cover_path):
            with console.status("[bold green]Downloading cover...", spinner="dots"):
                scraper.download_cover(metadata['cover_url'], cover_path)
            log_success("🖼️  Cover downloaded")
    else:
        cover_path = None

    # 3. TTS Generation
    log_info("🤖  Initializing TTS Engine... (this might take a moment)")
    tts = TTSEngine() # Load model once
    
    chapter_files = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task_id = progress.add_task("[cyan]Processing Chapters...", total=len(metadata['chapters']))
        
        for idx, chapter in enumerate(metadata['chapters']):
            safe_title = "".join(x for x in chapter['title'] if x.isalnum() or x in (' ', '_', '-')).strip()
            # Fallback for empty or complex titles
            if not safe_title:
                 safe_title = f"chapter_{idx}"
                 
            wav_filename = f"{idx:03d}_{safe_title}.wav"
            wav_path = os.path.join(cache_dir, wav_filename)
            
            progress.update(task_id, description=f"[cyan]Processing: {chapter['title']}")
            
            # Check if audio exists
            if os.path.exists(wav_path):
                # We can verify it, but for now just skip
                pass
            else:
                progress.console.print(f"Downloading text for: {chapter['title']}")
                text = scraper.get_chapter_text(chapter['url'])
                if not text:
                    log_warning(f"⚠️  Empty text for chapter: {chapter['title']}")
                    progress.advance(task_id)
                    continue

                # Stats
                num_paras = text.count('\n') + 1 # Basic paragraph count
                num_words = len(text.split())
                chunks = tts.chunk_text(text)
                
                log_info(f"  📊 Stats: {len(chunks)} chunks (sentences), {num_paras} paragraphs, {num_words} words")
                
                # Chunk Progress
                chunk_task = progress.add_task(f"[magenta]  Synthesizing...", total=len(chunks))
                
                segments = []
                silence = tts.get_silence()
                
                for chunk in chunks:
                    if not chunk.strip():
                        progress.advance(chunk_task)
                        continue
                    
                    try:
                        wav = tts.synthesize_text(chunk)
                        segments.append(wav)
                        segments.append(silence)
                    except Exception as e:
                        log_error(f"Error synthesising chunk: {e}")
                    
                    progress.advance(chunk_task)
                
                progress.remove_task(chunk_task)
                tts.save_to_file(segments, wav_path)
                
            if os.path.exists(wav_path):
                chapter_files.append({
                    'title': chapter['title'],
                    'file': wav_path
                })
            
            progress.advance(task_id)
    
    # 4. Build Audiobook
    safe_book_title = "".join(x for x in metadata['title'] if x.isalnum() or x in (' ', '_', '-')).strip()
    m4b_filename = f"{safe_book_title}.m4b"
    m4b_path = os.path.join(output_dir, m4b_filename)
    
    log_info("📦  Building M4B Container...")
    builder = AudiobookBuilder(cache_dir)
    builder.build_m4b(chapter_files, metadata, cover_path, m4b_path)
    
    log_success(f"🎉  Audiobook saved to: {m4b_path}")

if __name__ == '__main__':
    main()
