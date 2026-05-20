import re
from docx import Document


def extract_headings_from_md(filepath):
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()
    headings = []
    for i, line in enumerate(lines, 1):
        m = re.match(r'^(#{1,6})\s+(.+)', line.rstrip())
        if m:
            headings.append({"level": len(m.group(1)), "title": m.group(2).strip(), "line": i})
    return headings


def extract_headings_from_docx(filepath):
    doc = Document(filepath)
    headings = []
    for i, para in enumerate(doc.paragraphs, 1):
        style = para.style.name.lower()
        for lvl in range(1, 7):
            if f"heading {lvl}" in style and para.text.strip():
                headings.append({"level": lvl, "title": para.text.strip(), "line": i})
                break
    return headings


def check_toc(headings):
    issues = []
    warnings = []

    if not headings:
        issues.append("見出しが1つも見つかりませんでした。# や ## で見出しを付けてください。")
        return {"issues": issues, "warnings": warnings, "tree": []}

    levels = [h["level"] for h in headings]
    h1_count = levels.count(1)

    if h1_count == 0:
        issues.append("H1（# タイトル）が存在しません。書籍タイトルとしてH1を1つ設定してください。")
    elif h1_count > 1:
        warnings.append(f"H1が{h1_count}個あります。通常は1冊につき1つのH1が推奨されます。")

    # 階層のジャンプを検出（例: H1 → H3 で H2 スキップ）
    prev_level = 0
    for h in headings:
        if h["level"] > prev_level + 1 and prev_level != 0:
            warnings.append(
                f"見出し階層がスキップされています: H{prev_level} → H{h['level']} "
                f"「{h['title']}」（{h['line']}行目）"
            )
        prev_level = h["level"]

    # 重複見出し
    titles = [h["title"] for h in headings]
    seen = set()
    for t in titles:
        if t in seen:
            warnings.append(f"見出しが重複しています: 「{t}」")
        seen.add(t)

    # 見出しが長すぎる
    for h in headings:
        if len(h["title"]) > 60:
            warnings.append(f"見出しが長すぎます（{len(h['title'])}文字）: 「{h['title'][:30]}…」")

    return {"issues": issues, "warnings": warnings, "tree": headings}
