import argparse
import os
import sys
from .scraper import Scraper
from .tts_engine import TTSEngine
from .audiobook_builder import AudiobookBuilder

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
    
    print(f"--- Starting Audiobook Generation for Book ID: {book_id} ---")
    
    # 1. Scrape Metadata
    scraper = Scraper(book_id)
    try:
        metadata = scraper.get_book_metadata()
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        sys.exit(1)
        
    print(f"Title: {metadata['title']}")
    print(f"Author: {metadata['author']}")
    print(f"Found {len(metadata['chapters'])} chapters.")
    
    # 2. Download Cover
    cover_path = os.path.join(cache_dir, "cover.png")
    if metadata['cover_url']:
        if not os.path.exists(cover_path):
            scraper.download_cover(metadata['cover_url'], cover_path)
    else:
        cover_path = None

    # 3. TTS Generation
    tts = TTSEngine() # Load model once
    
    chapter_files = []
    
    for idx, chapter in enumerate(metadata['chapters']):
        safe_title = "".join(x for x in chapter['title'] if x.isalnum() or x in (' ', '_', '-')).strip()
        # Fallback for empty or complex titles
        if not safe_title:
             safe_title = f"chapter_{idx}"
             
        wav_filename = f"{idx:03d}_{safe_title}.wav"
        wav_path = os.path.join(cache_dir, wav_filename)
        
        print(f"Processing Chapter {idx+1}/{len(metadata['chapters'])}: {chapter['title']}")
        
        # Check if audio exists
        if os.path.exists(wav_path):
            print(f"  Skipping TTS (found {wav_filename})")
        else:
            text = scraper.get_chapter_text(chapter['url'])
            if not text:
                print("  Warning: Empty text for chapter.")
                # We can't skip adding it to the list otherwise metadata aligns wrong?
                # Actually if it's empty, maybe just skip it or create silence.
                # Let's create an empty/silent wav or just skip. 
                # If we skip, the M4B chapter list won't match TOC if we aren't careful.
                # But Scraper returns what it found. 
                # Let's try to synth even if empty? chunker handles it.
            
            tts.synthesize_chapter(text, wav_path)
            
        if os.path.exists(wav_path):
            chapter_files.append({
                'title': chapter['title'],
                'file': wav_path
            })
    
    # 4. Build Audiobook
    safe_book_title = "".join(x for x in metadata['title'] if x.isalnum() or x in (' ', '_', '-')).strip()
    m4b_filename = f"{safe_book_title}.m4b"
    m4b_path = os.path.join(output_dir, m4b_filename)
    
    builder = AudiobookBuilder(cache_dir)
    builder.build_m4b(chapter_files, metadata, cover_path, m4b_path)
    
    print(f"Title: {metadata['title']}")
    print(f"Success! Audiobook saved to: {m4b_path}")

if __name__ == '__main__':
    main()
