import os
import re
import uuid
import markdown
from ebooklib import epub
from bs4 import BeautifulSoup
from docx import Document


def md_to_html(text):
    return markdown.markdown(text, extensions=["extra", "toc"])


def docx_to_html(filepath):
    doc = Document(filepath)
    html_parts = []
    for para in doc.paragraphs:
        if not para.text.strip():
            continue
        style = para.style.name.lower()
        if "heading 1" in style:
            html_parts.append(f"<h1>{para.text}</h1>")
        elif "heading 2" in style:
            html_parts.append(f"<h2>{para.text}</h2>")
        elif "heading 3" in style:
            html_parts.append(f"<h3>{para.text}</h3>")
        else:
            html_parts.append(f"<p>{para.text}</p>")
    return "\n".join(html_parts)


def split_chapters(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    chapters = []
    current_title = "はじめに"
    current_content = []

    for tag in soup.children:
        if not hasattr(tag, "name"):
            continue
        if tag.name == "h1":
            if current_content:
                chapters.append((current_title, "".join(str(t) for t in current_content)))
            current_title = tag.get_text()
            current_content = []
        else:
            current_content.append(tag)

    if current_content:
        chapters.append((current_title, "".join(str(t) for t in current_content)))

    return chapters if chapters else [("本文", html_content)]


def create_epub(html_content, metadata, cover_path=None, output_dir="output"):
    book = epub.EpubBook()

    book.set_identifier(str(uuid.uuid4()))
    book.set_title(metadata.get("title", "無題"))
    book.set_language(metadata.get("language", "ja"))
    book.add_author(metadata.get("author", "著者名"))

    if metadata.get("description"):
        book.add_metadata("DC", "description", metadata["description"])
    if metadata.get("publisher"):
        book.add_metadata("DC", "publisher", metadata["publisher"])

    # 表紙画像
    if cover_path and os.path.exists(cover_path):
        with open(cover_path, "rb") as f:
            cover_data = f.read()
        ext = os.path.splitext(cover_path)[1].lower().lstrip(".")
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        book.set_cover(f"cover.{ext}", cover_data)

    # CSS
    style = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content="""
body { font-family: serif; line-height: 1.8; margin: 2em; }
h1 { font-size: 1.8em; border-bottom: 2px solid #333; padding-bottom: 0.3em; }
h2 { font-size: 1.4em; }
h3 { font-size: 1.2em; }
p { text-indent: 1em; margin: 0.5em 0; }
""",
    )
    book.add_item(style)

    # 章分割してEPUBページを作成
    chapters = split_chapters(html_content)
    epub_chapters = []

    for i, (title, content) in enumerate(chapters):
        chapter = epub.EpubHtml(
            title=title,
            file_name=f"chap_{i+1:03d}.xhtml",
            lang="ja",
        )
        chapter.content = f"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title>
<link rel="stylesheet" href="style/main.css"/></head>
<body><h1>{title}</h1>{content}</body></html>"""
        chapter.add_item(style)
        book.add_item(chapter)
        epub_chapters.append(chapter)

    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + epub_chapters

    safe_title = re.sub(r'[\\/:*?"<>|]', "_", metadata.get("title", "output"))
    out_path = os.path.join(output_dir, f"{safe_title}.epub")
    epub.write_epub(out_path, book)
    return out_path
