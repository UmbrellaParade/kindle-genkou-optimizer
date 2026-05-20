import re


ISSUES = [
    # 連続句読点
    (r"[。、]{2,}", "連続した句読点があります"),
    # 全角スペース
    (r"　", "全角スペースが含まれています"),
    # 半角カタカナ
    (r"[･-ﾟ]+", "半角カタカナが含まれています"),
    # 読点なし長文（100文字超で句読点なし）
    (r"[^\s。！？!?\n]{150,}", "句読点のない150文字以上の連続文が存在します"),
    # ... の代わりに…を使うべき
    (r"\.{3,}", "「...」の代わりに「…」の使用を検討してください"),
    # 同じ単語の繰り返し（5文字以上）
    (r"(.{5,})\1", "同じフレーズが繰り返されています"),
    # 感嘆符・疑問符の後にスペースなし（英文混じり）
    (r"[!?][^\s\n！？」』\)]", "「!」「?」の後にスペースがありません（英文混じりの場合）"),
    # 開きカッコと閉じカッコの不一致チェック用マーカー
]


def check_brackets(text):
    issues = []
    pairs = [("「", "」"), ("『", "』"), ("（", "）"), ("【", "】"), ("〔", "〕")]
    for open_b, close_b in pairs:
        opens = text.count(open_b)
        closes = text.count(close_b)
        if opens != closes:
            issues.append(
                f"カッコの対応がずれています: 「{open_b}」が{opens}個、「{close_b}」が{closes}個"
            )
    return issues


def proofread(text):
    findings = []

    for pattern, message in ISSUES:
        matches = list(re.finditer(pattern, text))
        if matches:
            examples = []
            for m in matches[:3]:
                start = max(0, m.start() - 10)
                end = min(len(text), m.end() + 10)
                ctx = text[start:end].replace("\n", " ")
                examples.append(f"「{ctx}」")
            findings.append({
                "type": "warning",
                "message": message,
                "count": len(matches),
                "examples": examples,
            })

    bracket_issues = check_brackets(text)
    for issue in bracket_issues:
        findings.append({"type": "error", "message": issue, "count": 1, "examples": []})

    return findings
