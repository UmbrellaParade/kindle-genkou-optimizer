import re


def fix_excess_blank_lines(text):
    """3行以上の連続空行を1行に圧縮"""
    return re.sub(r'\n{3,}', '\n\n', text)


def fix_trailing_spaces(text):
    """行末の半角・全角スペースを削除"""
    return re.sub(r'[ \t　]+$', '', text, flags=re.MULTILINE)


def fix_fullwidth_indent(text):
    """段落頭の全角スペースによる字下げを削除（CSSのtext-indentで代替）"""
    return re.sub(r'^　+', '', text, flags=re.MULTILINE)


def fix_single_linebreak(text):
    """単独改行（段落内改行）を段落区切りに変換

    日本語原稿でよくある「見た目の改行」を本来の段落区切りに直す。
    見出し行（# で始まる）や空行はそのまま保持する。
    """
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        is_blank = line.strip() == ''
        is_heading = line.strip().startswith('#')
        is_list = re.match(r'^[\s]*[-*+]|\d+\.', line.strip())

        # 空行・見出し・リストはそのまま
        if is_blank or is_heading or is_list:
            result.append(line)
            i += 1
            continue

        # 次の行が空行・見出し・リストでなければ空行を挿入して段落を分ける
        next_line = lines[i + 1] if i + 1 < len(lines) else ''
        next_is_blank = next_line.strip() == ''
        next_is_heading = next_line.strip().startswith('#')
        next_is_list = bool(re.match(r'^[\s]*[-*+]|\d+\.', next_line.strip()))

        result.append(line)
        if not next_is_blank and not next_is_heading and not next_is_list and next_line.strip() != '':
            result.append('')  # 段落区切りの空行を挿入
        i += 1

    return '\n'.join(result)


def fix_punctuation(text):
    """記号の統一"""
    # ... → …
    text = re.sub(r'\.{3,}', '…', text)
    # 。。や、、などの連続句読点を1つに
    text = re.sub(r'([。、])\1+', r'\1', text)
    return text


def fix_space_around_latin(text):
    """日本語と英数字の間のスペースを統一（半角スペース1つ）"""
    # 日本語→英数字
    text = re.sub(r'([^\x00-\x7F])([A-Za-z0-9])', r'\1 \2', text)
    # 英数字→日本語
    text = re.sub(r'([A-Za-z0-9])([^\x00-\x7F])', r'\1 \2', text)
    return text


FIXES = {
    "excess_blank_lines": ("連続する空行を1行に圧縮", fix_excess_blank_lines),
    "trailing_spaces":    ("行末の不要なスペースを削除", fix_trailing_spaces),
    "fullwidth_indent":   ("段落頭の全角スペース字下げを削除", fix_fullwidth_indent),
    "single_linebreak":   ("単独改行を段落区切りに変換（最重要）", fix_single_linebreak),
    "punctuation":        ("記号の統一（...→…、連続句読点）", fix_punctuation),
    "space_around_latin": ("日本語と英数字の間にスペースを挿入", fix_space_around_latin),
}


def apply_fixes(text, selected_fixes):
    for key, (_, fn) in FIXES.items():
        if key in selected_fixes:
            text = fn(text)
    return text
