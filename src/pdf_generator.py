from weasyprint import HTML, CSS
import os

class PDFBuilder:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def create_appendix(self, metadata, appendices, output_path):
        """
        Generates a PDF appendix containing images and footnotes.
        appendices: list of dicts {'chapter_title': str, 'images': [], 'footnotes': []}
        """
        html_content = self._generate_html(metadata, appendices)
        
        # Define styling
        css = CSS(string="""
            @page {
                size: A4;
                margin: 2.5cm;
                @bottom-right {
                    content: counter(page);
                }
            }
            body { font-family: serif; line-height: 1.6; }
            h1 { color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; border-bottom: 1px solid #eee; }
            h3 { color: #7f8c8d; font-size: 1.1em; margin-top: 20px; }
            .figure { margin: 20px 0; text-align: center; page-break-inside: avoid; }
            .figure img { max-width: 100%; height: auto; border: 1px solid #ddd; padding: 5px; }
            .caption { font-style: italic; color: #555; margin-top: 5px; font-size: 0.9em; }
            .footnotes { margin-top: 10px; }
            .footnote-item { margin-bottom: 8px; font-size: 0.95em; }
            .empty-msg { font-style: italic; color: #999; }
        """)
        
        HTML(string=html_content).write_pdf(output_path, stylesheets=[css])

    def _generate_html(self, metadata, appendices):
        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <title>{metadata['title']} - Appendix</title>
        </head>
        <body>
            <h1>{metadata['title']} - Appendix</h1>
            <p style="text-align: center; color: #666;">By {metadata['author']}</p>
        """
        
        has_content = False
        
        for chapter_data in appendices:
            items = chapter_data['data'] # {'images': [], 'footnotes': []}
            images = items.get('images', [])
            notes = items.get('footnotes', [])
            
            if not images and not notes:
                continue
                
            has_content = True
            html += f"<h2>{chapter_data['chapter_title']}</h2>"
            
            if images:
                html += "<h3>Figures & Images</h3>"
                for idx, img in enumerate(images, 1):
                    html += f"""
                    <div class="figure">
                        <img src="{img['src']}" alt="{img.get('alt', '')}">
                        <div class="caption">
                            <strong>Figure {idx}:</strong> {img.get('caption', '')}
                        </div>
                    """
                    # Add alt text and title if different from caption
                    alt = img.get('alt', '')
                    title = img.get('title', '')
                    if alt and alt != img.get('caption', ''):
                        html += f'<div class="caption" style="font-size: 0.85em; color: #777;">Alt: {alt}</div>'
                    if title and title != img.get('caption', '') and title != alt:
                        html += f'<div class="caption" style="font-size: 0.85em; color: #777;">Title: {title}</div>'
                    html += "</div>"
            
            if notes:
                html += "<h3>Footnotes</h3>"
                html += '<div class="footnotes"><ol>'
                for note in notes:
                    html += f'<li class="footnote-item">{note}</li>'
                html += '</ol></div>'

        if not has_content:
            html += "<p class='empty-msg'>No supplementary material (images or footnotes) found in this book.</p>"
            
        html += """
        </body>
        </html>
        """
        return html
