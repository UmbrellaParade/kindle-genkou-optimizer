import os
import json
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename
from modules.checker import analyze_text, extract_text_from_md, extract_text_from_docx
from modules.proofreader import proofread
from modules.converter import md_to_html, docx_to_html, create_epub

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


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)
    print("===== Kindle原稿最適化ツール =====")
    print("ブラウザで http://localhost:5000 を開いてください")
    app.run(debug=True, port=5000)
