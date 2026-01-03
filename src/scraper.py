import os
import requests
from bs4 import BeautifulSoup
import cairosvg

class Scraper:
    BASE_URL = "https://www.hindawi.org"

    def __init__(self, book_id):
        self.book_id = book_id
        self.book_url = f"{self.BASE_URL}/books/{book_id}/"
        self.session = requests.Session()

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

        # Title and Author
        # Usually in a header block. Structure might vary but typically H1/H2
        # Based on Hindawi structure:
        # <div class="book-header">
        #   <h1>Title</h1>
        #   <div class="author">Author</div>
        # </div>
        # We'll try to find them generically or specific classes if known.
        # Looking at public hindawi pages:
        # Title is often in <h1> inside user-content or similar, or just headers.
        
        # Let's try standard metadata tags or specific classes
        title_tag = soup.find('h1') or soup.find('h2') # Fallback
        title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

        author_tag = soup.find('div', class_='author') or soup.find('a', class_='author')
        author = author_tag.get_text(strip=True) if author_tag else "Unknown Author"

        # Cover Image
        # Often <div class="cover"><img src="..."></div>
        cover_div = soup.find('div', class_='image')
        cover_url = None
        if cover_div:
            img = cover_div.find('img')
            if img and img.get('src'):
                cover_url = img['src']
                if not cover_url.startswith('http'):
                    cover_url = self.BASE_URL + cover_url

        # Chapters from TOC
        # <div class="content"><ul><li><a href="...">...</a></li>...</ul></div>
        # Need to find the TOC list.
        chapters = []
        toc_div = soup.find('div', id='toc') or soup.find('div', class_='index')
        
        # If specific ID/class fails, generic search for links with book_id
        if toc_div:
             links = toc_div.find_all('a')
        else:
            # Fallback: look for all links containing the book ID in path, excluding the main page
            # This is risky, let's try to assume there is a list.
            # Hindawi structure usually has 'index' class for TOC
            links = soup.select('div.content ul li a')

        for link in links:
            href = link.get('href')
            if not href: continue
            
            # Ensure it's a chapter link (usually ends with a number or fractional number)
            # href might be relative
            full_url = href if href.startswith('http') else self.BASE_URL + href
            
            # Simple check: it must contain the book_id
            if self.book_id not in full_url:
                continue

            # Exclude the main page itself if caught
            if full_url.strip('/') == self.book_url.strip('/'):
                continue
                
            chapter_title = link.get_text(strip=True)
            chapters.append({
                'title': chapter_title,
                'url': full_url
            })

        return {
            'title': title,
            'author': author,
            'cover_url': cover_url,
            'chapters': chapters
        }

    def get_chapter_text(self, chapter_url):
        """
        Fetches the text content of a chapter.
        """
        print(f"Fetching text from {chapter_url}")
        response = self.session.get(chapter_url)
        if response.status_code == 404:
            print(f"Warning: Chapter {chapter_url} not found.")
            return ""
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extact text. Usually in a specific content div to avoid nav/footer.
        # <div id="media_2" ...> or similar?
        # Hindawi articles/books usually have a main content area.
        # Often <div class="chapter_content"> or similar.
        # Let's try getting paragraphs from the main container.
        
        # Strategies to find main text:
        content_div = soup.find('div', id='content') or soup.find('div', class_='content') or soup.body
        
        # remove scripts and styles
        for s in content_div(['script', 'style', 'header', 'footer', 'nav']):
            s.decompose()

        # Get all paragraphs
        paragraphs = content_div.find_all('p')
        text_content = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                text_content.append(text)
        
        return "\n\n".join(text_content)

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
