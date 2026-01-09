import fitz  # PyMuPDF
import os
from .logger import log_info, log_error

class DocumentExtractor:
    def __init__(self, file_path):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.doc = fitz.open(file_path)

    def get_metadata(self):
        """Extracts title and author from document metadata."""
        meta = self.doc.metadata
        return {
            'title': meta.get('title') or os.path.basename(self.file_path).rsplit('.', 1)[0],
            'author': meta.get('author') or "Unknown Author",
            'cover_url': None,
            'chapters': self.get_chapters()
        }

    def get_chapters(self):
        """
        Attempts to extract chapters based on document bookmarks (TOC).
        If no TOC is found, treats each page as a chapter.
        """
        toc = self.doc.get_toc()
        chapters = []

        if toc:
            log_info(f"Found TOC with {len(toc)} entries.")
            for i, entry in enumerate(toc):
                # entry is [level, title, page_number]
                level, title, page_num = entry
                if level == 1:  # Only take top-level chapters for now
                    chapters.append({
                        'title': title,
                        'page_num': page_num,
                        'index': i
                    })
        
        if not chapters:
            log_info("No TOC found or no top-level chapters. Using pages as chapters (limit to 100 for safety).")
            max_pages = min(self.doc.page_count, 100)
            for i in range(max_pages):
                chapters.append({
                    'title': f"Page {i+1}",
                    'page_num': i + 1,
                    'index': i
                })

        return chapters

    def get_chapter_content(self, chapter):
        """
        Extracts text for a specific chapter.
        """
        start_page = chapter['page_num'] - 1  # fitz uses 0-based indexing
        
        # Determine end page
        toc = self.doc.get_toc()
        if toc and 'index' in chapter:
            next_chapter_idx = chapter['index'] + 1
            if next_chapter_idx < len(toc):
                end_page = toc[next_chapter_idx][2] - 1
            else:
                end_page = self.doc.page_count
        else:
            # If fallback to pages, just one page
            end_page = start_page + 1

        text = ""
        # For EPUB, the concept of pages is different but PyMuPDF handles it.
        # However, EPUBs are often better extracted by chapter directly if possible.
        # PyMuPDF's get_text() on an EPUB page usually works well.
        for i in range(start_page, end_page):
            try:
                page = self.doc.load_page(i)
                text += page.get_text() + "\n"
            except Exception as e:
                log_error(f"Error extracting page {i}: {e}")

        return {
            'text': text.strip(),
            'appendix': {'images': [], 'footnotes': []},
            'audio_url': None
        }

    def close(self):
        self.doc.close()
