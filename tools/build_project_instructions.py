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
字数と構造の担保が弱くなる。可能ならリポジトリを Claude Code で開いて運用することを勧める。

---

■ここから下を「指示」欄に貼り付け■

"""

FOOTER = "\n■貼り付けここまで■\n"

MANUAL_COUNT_SECTION = """## 第1段階:自己申告

**本文を書き終えたら、次の表を自分で数えて出す。** 数えずに「守った」と書いてはならない。
右端は参照チャンネル全92本の実測で、しきい値の出所である。

| 項目 | 基準 | 実際 | 判定 | 参照92本 |
|---|---|---|---|---|
| 本文の総字数 | 5,600〜7,600字 | | | 中央値6,446字 |
| 総文数 | 150〜235文 | | | 中央値186文 |
| 一文の長さの中央値 | 27〜37字 | | | 中央値31字 |
| 段落数 | 36〜42(既定40) | | | 測定不能 |
| 200字以上の重量段落 | 4段落以上 | | | 測定不能 |
| P1に数字が無いか | 情景か逆説で始める | | | 上位回に例外なし |
| 研究文の最長連続 | 5文まで | | | 中央値3文 |
| 中盤の情景 | 3回 | | | 中央値3件 |
| 疑問文で終わる段落 | 4件以上 | | | 疑問文は中央値12文 |
| 巨視化 | 1件以上 | | | 中央値6件 |
| メタ発話 | 3件まで | | | 中央値1件 |
| 冒頭への回帰 | 入れるならP33〜P37 | | | 51パーセントのみ実行 |
| 想定反論の往復 | 3回以上。うち1回はP28以降 | | | 中央値3回 |
| 承認句のある段落 | 2件まで | | | 中央値1件 |
| 現代語への翻訳 | 3箇所以上(目安5) | | | 中央値1件。**自前で多く取る** |
| 限界と反証 | 1箇所以上 | | | 中央値0件。**完全に自前** |
| 二人称の呼びかけ | 8回以上 | | | 中央値12回 |
| 禁止記号 | 【】→:※!?…—()等が無い | | | TTS仕様 |
| 中黒の用法 | カタカナ名の区切りのみ | | | TTS仕様 |
| 英字の残存 | カタカナ化漏れが無い | | | TTS仕様 |
| 敬語 | 最終2段落のみ | | | 自前 |
| シグネチャ | 末尾が規定の締め文 | | | 固定 |

**1つでも基準を満たさない項目がある状態で納品してはならない。**

**なお、これらのしきい値は再生数の保証ではない。** 参照92本で18指標と再生数の
順位相関を取ったが、補正後に有意なものは一つも無かった。再生を動かすのは
テーマとタイトルである。

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
        "v4.0の監査は**ビート番号ではなく、錨と分布で判定する。**"
        "**FAILが1つでも残っている状態で納品してはならない。**\n\n"
        "機械チェックが通ったら、`references/audit.md` の目視チェック項目(機械では測れない質の項目)を1つずつ確認する。",
        "**下の「工程4 監査チェックリスト」を1項目ずつ確認する。** 字数・文数・研究文の連続・研究ゼロの区間は、"
        "本文を書いたあとに自分で数えて申告すること。数えずに「守った」と書いてはならない。"
        "不合格が1つでも残っている状態で納品してはならない。",
    )
    skill = skill.replace(
        "4. `tools/audit.py` を再実行して差分を報告する",
        "4. 書き直した段落の字数を数え、目標との差分を報告する",
    )
    # Project 運用にはファイル添付もローカル保存も無い
    skill = skill.replace(
        "ファイルは `output/<ディレクトリ>/` に4点(01素材台帳・02配分表・03台本・04制作メモ)保存する。\n\n"
        "**そのうえで、毎回必ず `03_台本.txt` を SendUserFile でチャットに添付して渡す。これは省略不可。** "
        "本文をチャットに長文で貼り付けるのではなく、AI音声にそのまま流し込めるファイルとして手渡す。"
        "増築モードで書き直したときも、再監査のあとに必ず添付し直す。\n\n"
        "制作メモも欲しいと言われた場合は、`04_制作メモ.md` を同じように添付する。",
        "この3つを、素材台帳→台本本文→制作メモの順に、ひとつの返答の中に出力する。"
        "台本本文は、見出しも注釈も混ぜずに、40段落を空行で区切ったプレーンテキストとして出す。"
        "その部分をそのままコピーすればAI音声へ流し込める状態にすること。",
    )
    parts.append(skill)

    for title, fn in [
        ("台本の型 v5.0", "beats.md"),
        ("書き方の規律", "style.md"),
        ("サムネイル生成プロンプトの作り方", "thumbnail.md"),
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
    text = text.replace("`references/beats.md`", "「台本の型 v5.0」の節")
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
