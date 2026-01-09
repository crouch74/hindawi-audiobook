import argparse
import os
import sys
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from .scraper import Scraper
from .tts_engine import TTSEngine
from .audiobook_builder import AudiobookBuilder
from .logger import console, log_info, log_success, log_error, log_warning

def main():
    parser = argparse.ArgumentParser(description="Convert Hindawi books or local PDFs/EPUBs to M4B audiobook.")
    parser.add_argument('book_id', nargs='?', help="The ID of the book on Hindawi.org (e.g., 46319638)")
    parser.add_argument('--file', '--pdf', dest='file', help="Path to a local PDF or EPUB file to convert")
    parser.add_argument('--lang', choices=['ar', 'en'], default=None, help="Language of the book (ar or en)")
    parser.add_argument('--output-dir', default='output', help="Directory to save the final M4B")
    parser.add_argument('--cache-dir', default='cache', help="Directory for intermediate files")
    parser.add_argument('--mode', choices=['audio', 'pdf', 'both'], default=None, 
                        help="Generation mode: audio, pdf, or both")
    parser.add_argument('--tts-provider', choices=['mms', 'edge', 'gtts', 'silero'], default=None,
                        help="TTS provider: mms, edge, gtts, or silero")
    parser.add_argument('--voice', default=None,
                        help="Voice for TTS")
    
    args = parser.parse_args()
    from rich.prompt import Prompt

    # --- Full Interactive Setup ---
    is_interactive = not args.book_id and not args.file
    
    source = None
    book_id = args.book_id
    file_path = args.file
    lang = args.lang
    mode = args.mode
    provider = args.tts_provider
    voice = args.voice

    if is_interactive:
        log_info("✨ Welcome to the Audiobook Generator Wizard!")
        source = Prompt.ask("Select book source", choices=["Hindawi.org", "Local File"], default="Hindawi.org")
        
        if source == "Hindawi.org":
            book_id = Prompt.ask("Enter Hindawi Book ID (e.g., 46319638)")
            if not book_id:
                log_error("❌ Book ID is required.")
                sys.exit(1)
        else:
            file_path = Prompt.ask("Enter path to PDF or EPUB file")
            if file_path:
                # Clean path: strip quotes and expand ~
                file_path = file_path.strip().strip('"').strip("'")
                file_path = os.path.expanduser(file_path)
                
            if not file_path or not os.path.exists(file_path):
                log_error(f"❌ File not found: {file_path}")
                sys.exit(1)

        if not lang:
            lang = Prompt.ask("Select book language", choices=["ar", "en"], default="ar")
            
        if not mode:
            log_info("🛠️  Select Generation Mode:")
            print("  1. Audio Only")
            print("  2. Appendix (PDF) Only")
            print("  3. Both (Audio + Appendix)")
            m_choice = Prompt.ask("Choose mode", choices=["1", "2", "3"], default="3")
            mode = {'1': 'audio', '2': 'pdf', '3': 'both'}[m_choice]
    else:
        # Fallback defaults for missing args in semi-interactive mode
        if not lang: lang = "ar"
        if not mode: mode = "audio"

    output_dir = args.output_dir

    # --- Processing logic starts here ---
    if file_path:
        from .document_extractor import DocumentExtractor
        book_id = os.path.basename(file_path).rsplit('.', 1)[0]
        cache_dir = os.path.join(args.cache_dir, book_id)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        log_info(f"🚀  Starting Audiobook Generation for File: {file_path}")
        
        extractor = DocumentExtractor(file_path)
        metadata = extractor.get_metadata()
        scraper = None
    else:
        # If still no book_id by now, it's an error
        if not book_id:
            parser.print_help()
            sys.exit(1)
            
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
    
    # 2. Download Cover (only for scraped books)
    cover_path = os.path.join(cache_dir, "cover.png")
    if not file_path and metadata['cover_url']:
        if not os.path.exists(cover_path):
            with console.status("[bold green]Downloading cover...", spinner="dots"):
                scraper.download_cover(metadata['cover_url'], cover_path)
            log_success("🖼️  Cover downloaded")
    elif file_path:
        cover_path = None
    else:
        cover_path = None

    generate_audio = mode in ["audio", "both"]
    generate_pdf = mode in ["pdf", "both"]

    # 4. TTS Selection (Only if audio)
    if generate_audio:
        if provider and (voice or provider != 'edge'):
            # Already have provider (and voice if edge)
            pass
        else:
            # Interactive or semi-interactive selection
            from .tts_engine import TTS_PROVIDERS
            
            log_info(f"🔊  Select TTS Provider (Language: {lang}):")
            available_providers = list(TTS_PROVIDERS.keys())
            if lang != 'ar' and 'silero' in available_providers:
                available_providers.remove('silero')
                
            for key in available_providers:
                info = TTS_PROVIDERS[key]
                print(f"  {key}: {info['name']} [{info['type']}]")
            
            if not provider:
                provider = Prompt.ask("Choose provider", choices=available_providers, default="edge")
            
            if not voice:
                if provider == "mms":
                    voice = "facebook/mms-tts-ara" if lang == "ar" else "facebook/mms-tts-eng"
                elif provider == "gtts":
                    voice = lang
                elif provider == "silero":
                    voice = "xglm_v1"
                elif provider == "edge":
                    if lang == "ar":
                        log_info("🗣️  Select Arabic Voice:")
                        print("  1. Salma (Egypt - Female)")
                        print("  2. Shakir (Egypt - Male)")
                        print("  3. Hamed (Saudi Arabia - Male)")
                        print("  4. Zariyah (Saudi Arabia - Female)")
                        voice_map = {"1": "ar-EG-SalmaNeural", "2": "ar-EG-ShakirNeural", "3": "ar-SA-HamedNeural", "4": "ar-SA-ZariyahNeural"}
                        v_choice = Prompt.ask("Choose voice", choices=["1", "2", "3", "4"], default="1")
                        voice = voice_map[v_choice]
                    else:
                        log_info("🗣️  Select English Voice:")
                        print("  1. Andrew (US - Male)")
                        print("  2. Ava (US - Female)")
                        print("  3. Emma (UK - Female)")
                        print("  4. Brian (UK - Male)")
                        voice_map = {"1": "en-US-AndrewNeural", "2": "en-US-AvaNeural", "3": "en-GB-EmmaNeural", "4": "en-GB-BrianNeural"}
                        v_choice = Prompt.ask("Choose voice", choices=["1", "2", "3", "4"], default="1")
                        voice = voice_map[v_choice]

        log_info(f"🤖  Initializing TTS Engine ({provider} - {voice})...")
        tts = TTSEngine(provider=provider, voice=voice, lang=lang)
    else:
        tts = None
    
    chapter_files = []
    appendices_data = []
    
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
            
            # Use cached extraction if we skip TTS? Ideally re-scrape to get images if PDF requested
            # But scraper doesn't cache scrape results to disk yet.
            # We must scrape.
            
            progress.console.print(f"Fetching content for: {chapter['title']}")
            if scraper:
                content_data = scraper.get_chapter_content(chapter['url'])
            else:
                content_data = extractor.get_chapter_content(chapter)
                
            text = content_data['text']
            audio_url = content_data.get('audio_url')
            
            # Store appendix info
            appendices_data.append({
                'chapter_title': chapter['title'],
                'data': content_data['appendix']
            })

            # Check if audio exists
            if generate_audio:
                if os.path.exists(wav_path):
                    # Audio already cached
                    pass
                elif audio_url:
                    # Pre-recorded audio exists - download it instead of TTS
                    log_info(f"  🎵 Downloading pre-recorded audio...")
                    
                    # Download to temporary location (might be MP3)
                    temp_audio_path = wav_path.replace('.wav', '_temp.mp3')
                    
                    if scraper.download_audio(audio_url, temp_audio_path):
                        # Convert to WAV if needed
                        if temp_audio_path.endswith('.mp3'):
                            try:
                                from pydub import AudioSegment
                                audio = AudioSegment.from_mp3(temp_audio_path)
                                audio.export(wav_path, format='wav')
                                os.remove(temp_audio_path)
                                log_success(f"  ✓ Audio downloaded and converted")
                            except Exception as e:
                                log_error(f"  Error converting audio: {e}")
                                # Keep the MP3 if conversion fails
                                os.rename(temp_audio_path, wav_path.replace('.wav', '.mp3'))
                        else:
                            os.rename(temp_audio_path, wav_path)
                    else:
                        log_warning(f"  ⚠️  Failed to download audio, will use TTS instead")
                        audio_url = None  # Fall back to TTS
                
                # If no pre-recorded audio, use TTS
                if not audio_url and not os.path.exists(wav_path):
                    if not text:
                        log_warning(f"⚠️  Empty text for chapter: {chapter['title']}")
                        progress.advance(task_id)
                        continue

                    # Stats
                    num_paras = text.count('\n') + 1 
                    num_words = len(text.split())
                    chunks = tts.chunk_text(text)
                    
                    log_info(f"  📊 Stats: {len(chunks)} chunks, {num_paras} paras, {num_words} words")
                    
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
    
    # 5. Build Artifacts
    safe_book_title = "".join(x for x in metadata['title'] if x.isalnum() or x in (' ', '_', '-')).strip()
    
    if generate_audio:
        m4b_filename = f"{safe_book_title}.m4b"
        m4b_path = os.path.join(output_dir, m4b_filename)
        log_info("📦  Building M4B Container...")
        builder = AudiobookBuilder(cache_dir)
        builder.build_m4b(chapter_files, metadata, cover_path, m4b_path)
        log_success(f"🎉  Audiobook saved to: {m4b_path}")
        
    if generate_pdf and scraper:
        from .pdf_generator import PDFBuilder
        pdf_filename = f"{safe_book_title}_Appendix.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        log_info("📄  Generating Appendix PDF...")
        pdf_builder = PDFBuilder(output_dir)
        pdf_builder.create_appendix(metadata, appendices_data, pdf_path)
        log_success(f"🎉  Appendix saved to: {pdf_path}")

    if not scraper:
        extractor.close()

if __name__ == '__main__':
    main()
