#!/usr/bin/env python3
"""Claude Project の「指示」欄に貼る1枚指示書を生成する。

スキル(.claude/skills/daihon/)を唯一の正とし、そこから連結して dist/ に出力する。
スキルを編集したら、このスクリプトを再実行して dist を同期させること。

    python3 tools/build_project_instructions.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, ".claude", "skills", "daihon")
OUT = os.path.join(ROOT, "dist", "project-instructions.md")

HEADER = """# 台本生成システム v3.1「構造解剖ch」プロジェクト指示書

このファイルは `.claude/skills/daihon/` から自動生成されている。**直接編集しない。**
編集はスキル側で行い、`python3 tools/build_project_instructions.py` で再生成する。

使い方:下の■内を Claude Project の「指示」欄に全文貼り付け、ナレッジに `knowledge/` 以下をアップロードする。

注意:Project 運用では機械監査 `tools/audit.py` が使えない。工程4の第1段階は目視に置き換わるため、
字数とビートの担保が弱くなる。可能ならリポジトリを Claude Code で開いて運用することを勧める。

---

■ここから下を「指示」欄に貼り付け■

"""

FOOTER = "\n■貼り付けここまで■\n"

MANUAL_COUNT_SECTION = """## 第1段階:字数の自己申告

**本文を書き終えたら、41ビートそれぞれの字数を数えて表にして出す。** 数えずに「守った」と書いてはならない。

| ビート | 役割 | 目標 | 実際 | 判定 |
|---|---|---|---|---|

判定基準:

| 項目 | 基準 |
|---|---|
| 本文の総字数 | 6,500字以上 |
| 段落数 | 41(ビート40の省略時は40) |
| ビート別字数 | 各ビートが目標字数の80パーセント以上 |
| 重量級ビート10・17・24・30・37 | 各200字以上 |
| ブロック末尾13・20・27・32・36 | 疑問文で終わる |
| 裏切り予告(ビート13)の位置 | 全体の22〜55パーセント地点 |
| 禁止記号 | 【】→:※!?…—()等が本文に無い |
| 中黒の用法 | カタカナ名の区切り以外に使われていない |
| 英字の残存 | カタカナ化漏れが無い(定着略称は除外) |
| シグネチャ | 末尾が規定の締め文 |

**1つでも基準を満たさない項目がある状態で納品してはならない。**

"""


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def strip_frontmatter(text):
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S).lstrip()


def demote(text, levels=1):
    """見出しレベルを下げて、連結後の階層を揃える。"""
    return re.sub(r"^(#{1,5}) ", lambda m: "#" * (len(m.group(1)) + levels) + " ", text, flags=re.M)


def main():
    parts = [HEADER]

    skill = strip_frontmatter(read(os.path.join(SKILL, "SKILL.md")))
    # 機械監査への参照を、Project運用で意味の通る表現に差し替える
    skill = skill.replace(
        "まず機械チェックを走らせる:\n\n```bash\npython3 tools/audit.py output/<ディレクトリ>/03_台本.txt\n```\n\n"
        "このツールは字数・段落数・ビート別字数・禁止記号・ブロック末尾の疑問文・裏切り予告の位置・カタカナ化漏れを自動判定する。"
        "**FAILが1つでも残っている状態で納品してはならない。**\n\n"
        "機械チェックが通ったら、`references/audit.md` の目視チェック項目(機械では測れない質の項目)を1つずつ確認する。",
        "**下の「工程4 監査チェックリスト」を1項目ずつ確認する。** 特に各ビートの字数は、本文を書いたあとに"
        "自分で数えて申告すること。数えずに「守った」と書いてはならない。不合格が1つでも残っている状態で納品してはならない。",
    )
    skill = skill.replace(
        "4. `tools/audit.py` を再実行して差分を報告する",
        "4. 書き直した段落の字数を数え、目標字数との差分を報告する",
    )
    parts.append(skill)

    for title, fn in [
        ("41ビート設計図", "beats.md"),
        ("書き方の規律", "style.md"),
        ("工程4 監査チェックリスト", "audit.md"),
    ]:
        body = read(os.path.join(SKILL, "references", fn))
        body = re.sub(r"^# .*\n", "", body, count=1)
        if fn == "audit.md":
            # 機械チェックの節を、Project運用の自己申告チェックに差し替える
            body = re.sub(
                r"## 第1段階:機械チェック.*?(?=## 第2段階)",
                MANUAL_COUNT_SECTION,
                body,
                flags=re.S,
            )
            body = body.replace("## 第2段階:目視チェック(機械では測れない項目)", "## 第2段階:目視チェック")
            body = body.replace("機械チェックが通ってから、", "第1段階が通ってから、")
        parts.append("\n---\n\n# " + title + "\n" + demote(body))

    text = "\n".join(parts) + FOOTER
    # Project運用に存在しないパス参照を整理
    text = text.replace("`references/beats.md`", "「41ビート設計図」の節")
    text = text.replace("`references/style.md`", "「書き方の規律」の節")
    text = text.replace("`references/audit.md`", "「工程4 監査チェックリスト」の節")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)

    chars = len(text)
    print(f"生成: {os.path.relpath(OUT, ROOT)}  {chars:,}文字")
    if chars > 30000:
        print("警告: Project の指示欄の上限を超える可能性がある", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
