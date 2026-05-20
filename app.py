import os
import json
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename
from modules.checker import analyze_text, extract_text_from_md, extract_text_from_docx
from modules.proofreader import proofread
from modules.converter import md_to_html, docx_to_html, create_epub
from modules.formatter import apply_fixes, FIXES
from modules.toc_checker import extract_headings_from_md, extract_headings_from_docx, check_toc
from PIL import Image

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["OUTPUT_FOLDER"] = "output"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

ALLOWED_EXTENSIONS = {"md", "txt", "docx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_text(filepath, ext):
    if ext in ("md", "txt"):
        return extract_text_from_md(filepath)
    elif ext == "docx":
        return extract_text_from_docx(filepath)
    return ""


def get_html(filepath, ext):
    if ext in ("md", "txt"):
        with open(filepath, encoding="utf-8") as f:
            return md_to_html(f.read())
    elif ext == "docx":
        return docx_to_html(filepath)
    return ""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/check", methods=["POST"])
def api_check():
    if "file" not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400
    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "対応していないファイル形式です（.md / .txt / .docx）"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    ext = filename.rsplit(".", 1)[1].lower()
    chars_per_page = int(request.form.get("chars_per_page", 400))

    try:
        text = get_text(filepath, ext)
        stats = analyze_text(text, chars_per_page)
        issues = proofread(text)
        return jsonify({"stats": stats, "issues": issues})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/format", methods=["POST"])
def api_format():
    if "file" not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400
    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "対応していないファイル形式です（.md / .txt / .docx）"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    ext = filename.rsplit(".", 1)[1].lower()
    selected_fixes = request.form.getlist("fixes")

    try:
        original = extract_text_from_md(filepath) if ext in ("md", "txt") else extract_text_from_docx(filepath)

        # .docx の場合は元のMarkdownテキストとして扱えないのでMD変換は行わない
        if ext == "docx":
            return jsonify({"error": ".docx は整形機能に対応していません。先に .md または .txt で保存してください"}), 400

        with open(filepath, encoding="utf-8") as f:
            raw = f.read()

        fixed = apply_fixes(raw, selected_fixes)

        # 整形済みファイルを保存してダウンロード用パスを返す
        out_filename = f"formatted_{filename}"
        out_path = os.path.join(app.config["OUTPUT_FOLDER"], out_filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(fixed)

        before_html = md_to_html(raw)
        after_html = md_to_html(fixed)

        return jsonify({"before": before_html, "after": after_html, "out_filename": out_filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download-formatted/<filename>")
def download_formatted(filename):
    path = os.path.join(app.config["OUTPUT_FOLDER"], secure_filename(filename))
    if not os.path.exists(path):
        return "ファイルが見つかりません", 404
    return send_file(path, as_attachment=True, download_name=filename)


@app.route("/api/preview", methods=["POST"])
def api_preview():
    if "file" not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400
    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "対応していないファイル形式です（.md / .txt / .docx）"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    ext = filename.rsplit(".", 1)[1].lower()
    try:
        html_content = get_html(filepath, ext)
        return jsonify({"html": html_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/convert", methods=["POST"])
def api_convert():
    if "file" not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400
    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "対応していないファイル形式です（.md / .txt / .docx）"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    ext = filename.rsplit(".", 1)[1].lower()

    metadata = {
        "title": request.form.get("title", "無題"),
        "author": request.form.get("author", "著者名"),
        "description": request.form.get("description", ""),
        "publisher": request.form.get("publisher", ""),
        "language": request.form.get("language", "ja"),
    }

    cover_path = None
    if "cover" in request.files and request.files["cover"].filename:
        cover_file = request.files["cover"]
        cover_filename = secure_filename(cover_file.filename)
        cover_path = os.path.join(app.config["UPLOAD_FOLDER"], cover_filename)
        cover_file.save(cover_path)

    try:
        html_content = get_html(filepath, ext)
        out_path = create_epub(html_content, metadata, cover_path, app.config["OUTPUT_FOLDER"])
        return send_file(out_path, as_attachment=True, download_name=os.path.basename(out_path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/toc-check", methods=["POST"])
def api_toc_check():
    if "file" not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400
    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "対応していないファイル形式です（.md / .txt / .docx）"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    ext = filename.rsplit(".", 1)[1].lower()

    try:
        headings = extract_headings_from_md(filepath) if ext in ("md", "txt") else extract_headings_from_docx(filepath)
        result = check_toc(headings)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cover-check", methods=["POST"])
def api_cover_check():
    if "cover" not in request.files:
        return jsonify({"error": "画像が選択されていません"}), 400
    file = request.files["cover"]
    if not file.filename:
        return jsonify({"error": "ファイルを選択してください"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        img = Image.open(filepath)
        w, h = img.size
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        ratio = round(h / w, 2) if w > 0 else 0

        checks = []
        passed = True

        # 最低サイズ: 625x1000px
        if w >= 625 and h >= 1000:
            checks.append({"ok": True,  "msg": f"サイズ OK ({w} x {h} px)"})
        else:
            checks.append({"ok": False, "msg": f"サイズ不足 ({w} x {h} px)。最低 625 x 1000 px 必要です"})
            passed = False

        # 推奨サイズ: 1600x2560px
        if w >= 1600 and h >= 2560:
            checks.append({"ok": True,  "msg": "推奨サイズ以上 (1600 x 2560 px)"})
        else:
            checks.append({"ok": None,  "msg": f"推奨サイズ未満です。1600 x 2560 px を推奨します"})

        # 縦横比: 高さ/幅 ≒ 1.6
        if 1.4 <= ratio <= 1.8:
            checks.append({"ok": True,  "msg": f"縦横比 OK ({ratio}:1 ≒ 1.6:1)"})
        else:
            checks.append({"ok": False, "msg": f"縦横比が推奨外です ({ratio}:1)。高さ÷幅 ≒ 1.6 が推奨です"})
            passed = False

        # ファイルサイズ: 50MB以下
        if size_mb <= 50:
            checks.append({"ok": True,  "msg": f"ファイルサイズ OK ({size_mb:.1f} MB)"})
        else:
            checks.append({"ok": False, "msg": f"ファイルサイズ超過 ({size_mb:.1f} MB)。50 MB 以下にしてください"})
            passed = False

        # 形式
        fmt = img.format or "不明"
        if fmt.upper() in ("JPEG", "PNG"):
            checks.append({"ok": True,  "msg": f"形式 OK ({fmt})"})
        else:
            checks.append({"ok": False, "msg": f"非対応の形式です ({fmt})。JPG または PNG を使用してください"})
            passed = False

        return jsonify({"passed": passed, "width": w, "height": h, "checks": checks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/description-html", methods=["POST"])
def api_description_html():
    text = request.form.get("description", "").strip()
    if not text:
        return jsonify({"error": "説明文を入力してください"}), 400

    import re as _re
    lines = text.splitlines()
    html_parts = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        # 箇条書き（- or * で始まる）
        if line.startswith(("- ", "* ", "・")):
            items = []
            while i < len(lines) and lines[i].strip().startswith(("- ", "* ", "・")):
                item = _re.sub(r'^[-*・]\s*', '', lines[i].strip())
                item = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', item)
                item = _re.sub(r'\*(.+?)\*', r'<i>\1</i>', item)
                items.append(f"<li>{item}</li>")
                i += 1
            html_parts.append("<ul>" + "".join(items) + "</ul>")
            continue
        # 小見出し（### or ## で始まる）
        if line.startswith("### "):
            content = _re.sub(r'^###\s*', '', line)
            html_parts.append(f"<h6>{content}</h6>")
        elif line.startswith("## "):
            content = _re.sub(r'^##\s*', '', line)
            html_parts.append(f"<h5>{content}</h5>")
        elif line.startswith("# "):
            content = _re.sub(r'^#\s*', '', line)
            html_parts.append(f"<h4>{content}</h4>")
        else:
            # インライン太字・斜体
            p = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
            p = _re.sub(r'\*(.+?)\*', r'<i>\1</i>', p)
            html_parts.append(f"<p>{p}</p>")
        i += 1

    html_output = "\n".join(html_parts)
    return jsonify({"html": html_output})


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)
    print("===== Kindle原稿最適化ツール =====")
    print("ブラウザで http://localhost:5000 を開いてください")
    app.run(debug=True, port=5000)
