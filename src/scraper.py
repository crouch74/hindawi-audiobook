import os
import requests
import cloudscraper
from bs4 import BeautifulSoup
import cairosvg

class Scraper:
    BASE_URL = "https://www.hindawi.org"

    def __init__(self, book_id):
        self.book_id = book_id
        self.book_url = f"{self.BASE_URL}/books/{book_id}/"
        # Allow cloudscraper to handle browser emulation matching the container's OS (Linux)
        self.session = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'linux', 'desktop': True}
        )
        # Add only non-conflicting headers
        self.session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Referer': 'https://www.google.com/',
        })

    def get_book_metadata(self):
        """
        Fetches the book main page and extracts:
        - Title
        - Author
        - Cover Image URL
        - List of Chapters (Url, Title)
        """
        print(f"Fetching metadata from {self.book_url}")
        response = self.session.get(self.book_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Title
        # Try OpenGraph title first
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content']
        else:
            title_tag = soup.find('h1') or soup.find('h2')
            title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

        # 2. Author
        # Try standard meta author or Hindawi specific
        # Often in <div class="author"> or <a href="...">Names</a>
        author_tag = soup.find('div', class_='author') or soup.find('a', class_='author')
        if author_tag:
             author = author_tag.get_text(strip=True)
        else:
             # Fallback
             author = "Unknown Author"

        # 3. Cover Image
        # Try og:image
        og_image = soup.find('meta', property='og:image')
        cover_url = None
        if og_image and og_image.get('content'):
            cover_url = og_image['content']
        else:
            # Fallback
            cover_div = soup.find('div', class_='image') or soup.find('div', class_='bookCover')
            if cover_div:
                img = cover_div.find('img')
                if img and img.get('src'):
                    cover_url = img['src']
        
        if cover_url and not cover_url.startswith('http'):
            cover_url = self.BASE_URL + cover_url

        # 4. Chapters
        # Broad search for all links containing the book ID
        chapters = []
        seen_urls = set()
        
        # Start looking for links
        # Filter all links
        for link in soup.find_all('a'):
            href = link.get('href')
            if not href: continue
            
            # Normalize URL
            full_url = href if href.startswith('http') else self.BASE_URL + href
            if not full_url.endswith('/'):
                 full_url += '/'
                 
            # Must contain book_id
            if str(self.book_id) not in full_url:
                continue
            
            # Exclude the main page itself
            # Main page:  .../books/ID/
            # Chapters:   .../books/ID/X.Y/ or .../books/ID/chapter/
            if full_url.rstrip('/') == self.book_url.rstrip('/'):
                continue
            
            # Exclude known external or download patterns
            if any(x in full_url for x in ['facebook.com', 'twitter.com', 'whatsapp://', 'linkedin.com', 'sharer', 'plus.google.com']):
                continue
            
            if 'downloads.hindawi.org' in full_url:
                continue
                
            # Exclude PDF/ePub/KFX links usually found in sidebars
            if any(full_url.endswith(ext) for ext in ['.pdf', '.epub', '.kfx', '.mobi']):
                continue

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            chapter_title = link.get_text(strip=True)
            # Filter out numeric only titles if they are just pagination? 
            # No, keep them.
            
            # If title is empty, maybe skip
            if not chapter_title:
                continue

            chapters.append({
                'title': chapter_title,
                'url': full_url
            })
        
        # Sort chapters by URL just in case, though they appear in order in DOM usually.
        # But robust finding might mix order.
        # Let's rely on DOM order which `find_all` preserves.

        return {
            'title': title,
            'author': author,
            'cover_url': cover_url,
            'chapters': chapters
        }

    def get_chapter_content(self, chapter_url):
        """
        Fetches chapter content, separating narrative text from appendix items (images, footnotes).
        Returns dict: {'text': str, 'appendix': {'images': [], 'footnotes': []}}
        """
        print(f"Fetching content from {chapter_url}")
        response = self.session.get(chapter_url)
        if response.status_code == 404:
            print(f"Warning: Chapter {chapter_url} not found.")
            return {'text': "", 'appendix': {'images': [], 'footnotes': []}}
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        content_div = soup.find(class_='chapterContent') or soup.find('div', id='content') or soup.find('div', class_='content') or soup.body
        
        # Remove scripts, styles, and navigation
        for s in content_div(['script', 'style', 'header', 'footer', 'nav']):
            s.decompose()
            
        appendix = {'images': [], 'footnotes': []}
        
        # 1. Extract Images (Figures with captions)
        for fig in content_div.find_all('figure'):
            img = fig.find('img')
            if img and img.get('src'):
                src = img['src']
                if not src.startswith('http'): 
                    src = self.BASE_URL + src if src.startswith('/') else src
                
                # Get caption from figcaption
                cap = fig.find('figcaption')
                caption = cap.get_text(strip=True) if cap else ""
                
                # Get alt text and title
                alt_text = img.get('alt', '')
                title = img.get('title', '')
                
                # Combine caption sources
                full_caption = caption or alt_text or title or ""
                
                appendix['images'].append({
                    'src': src, 
                    'caption': full_caption,
                    'alt': alt_text,
                    'title': title
                })
            fig.decompose()
            
        # Extract standalone images (not in figures)
        for img in content_div.find_all('img'):
             src = img.get('src')
             if src:
                 if not src.startswith('http'): 
                     src = self.BASE_URL + src if src.startswith('/') else src
                 
                 alt_text = img.get('alt', '')
                 title = img.get('title', '')
                 
                 # Look for caption in parent or sibling elements
                 caption = ""
                 parent = img.parent
                 if parent and parent.name == 'div':
                     # Check for caption class siblings
                     caption_el = parent.find(class_='caption') or parent.find(class_='img-caption')
                     if caption_el:
                         caption = caption_el.get_text(strip=True)
                 
                 full_caption = caption or alt_text or title or ""
                 
                 appendix['images'].append({
                     'src': src, 
                     'caption': full_caption,
                     'alt': alt_text,
                     'title': title
                 })
             img.decompose()
             
        # 2. Extract Footnotes
        # Method 1: Footnotes div with list
        for fn_div in content_div.find_all(class_='footnotes'):
            for li in fn_div.find_all('li'):
                appendix['footnotes'].append(li.get_text(strip=True))
            fn_div.decompose()
        
        # Method 2: Individual footnote divs
        for fn in content_div.find_all(class_='footnote'):
            text = fn.get_text(strip=True)
            if text:
                appendix['footnotes'].append(text)
            fn.decompose()
            
        # Method 3: Aside elements (often used for footnotes)
        for aside in content_div.find_all('aside'):
            text = aside.get_text(strip=True)
            if text and len(text) > 10:  # Avoid empty or very short asides
                appendix['footnotes'].append(text)
            aside.decompose()
            
        # Cleanup remaining markers/classes
        for sup in content_div.find_all('sup'):
            sup.decompose()
            
        for class_name in ['caption', 'img-container', 'marginal', 'img-caption']:
             for el in content_div.find_all(class_=class_name):
                 el.decompose()

        # Get all paragraphs
        paragraphs = content_div.find_all('p')
        text_content = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                text_content.append(text)
        
        return {
            'text': "\n\n".join(text_content),
            'appendix': appendix
        }

    def download_cover(self, url, output_path):
        """
        Downloads cover image. If SVG, converts to PNG.
        """
        if not url:
            return False
            
        print(f"Downloading cover from {url}")
        response = self.session.get(url)
        response.raise_for_status()
        
        # Check if SVG
        if url.lower().endswith('.svg') or b'<svg' in response.content[:100]:
            # Convert to PNG
            try:
                cairosvg.svg2png(bytestring=response.content, write_to=output_path)
                return True
            except Exception as e:
                print(f"Error converting SVG cover: {e}")
                return False
        else:
            # Save directly
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
