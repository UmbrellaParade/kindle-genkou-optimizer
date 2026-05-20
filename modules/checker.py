import re
from docx import Document


def extract_text_from_md(filepath):
    with open(filepath, encoding="utf-8") as f:
        text = f.read()
    # Markdownの記号を除去してプレーンテキスト化
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", text)
    return text


def extract_text_from_docx(filepath):
    doc = Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs)


def analyze_text(text, chars_per_page=400):
    lines = text.splitlines()
    sentences = re.split(r"[。！？!?]", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    total_chars = len(re.sub(r"\s", "", text))
    total_with_space = len(text)
    pages = max(1, round(total_chars / chars_per_page))

    long_sentences = [s for s in sentences if len(s) > 100]

    # 章ごとの文字数
    chapters = []
    current_chapter = None
    current_chars = 0
    for line in lines:
        if re.match(r"^#{1,3}\s+", line):
            if current_chapter is not None:
                chapters.append({"title": current_chapter, "chars": current_chars})
            current_chapter = re.sub(r"^#{1,3}\s+", "", line)
            current_chars = 0
        else:
            current_chars += len(re.sub(r"\s", "", line))
    if current_chapter is not None:
        chapters.append({"title": current_chapter, "chars": current_chars})

    return {
        "total_chars": total_chars,
        "total_with_space": total_with_space,
        "estimated_pages": pages,
        "sentence_count": len(sentences),
        "long_sentence_count": len(long_sentences),
        "long_sentences": long_sentences[:5],
        "chapters": chapters,
        "line_count": len([l for l in lines if l.strip()]),
    }
