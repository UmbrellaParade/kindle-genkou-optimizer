# 📚 Kindle原稿最適化ツール

Markdown / Word (.docx) ファイルをKindle出版向けに最適化・変換するWebアプリです。

## 機能

- **文字数・ページ数チェック** — 総文字数・推定ページ数・章別集計
- **品質チェック** — 連続句読点・カッコ不一致・長文など自動検出
- **EPUB変換** — KDP（Kindle Direct Publishing）に直接入稿できるEPUBを生成
- **メタデータ管理** — タイトル・著者・説明文・表紙画像を設定

## セットアップ

```bash
# 1. 依存パッケージのインストール
pip install -r requirements.txt

# 2. アプリ起動
python app.py
```

ブラウザで `http://localhost:5000` を開いてください。

## 対応ファイル形式

| 入力 | 出力 |
|------|------|
| `.md` (Markdown) | `.epub` |
| `.txt` | `.epub` |
| `.docx` (Word) | `.epub` |

## KDP入稿のポイント

- AmazonはEPUB形式を推奨（MOBIは廃止予定）
- 表紙画像の推奨: 2560×1600px（比率1.6:1）、JPG/PNG
- 生成したEPUBはKDP管理画面からそのまま入稿可能

## ライセンス

MIT
