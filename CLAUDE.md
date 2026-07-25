# yt-tetsugaku_daihon

教養系YouTubeチャンネル「構造解剖ch」の台本生成システム v3.1。

## これは何か

誰もが知る俗な現象を、実在の学術研究と精密な統計で解剖し、最後に視聴者自身へ矛先を返す「構造解剖型」の台本を、**41ビート(段落)の設計図に沿って**生成する。出力はAI音声にそのまま読ませられるプレーンテキスト。

厚みと密度は執筆時の努力ではなく、**工程そのもの**が保証する。素材を先に15行分集め、41ビートに割り付けてから書き始める。

## 使い方

Claude Code でこのリポジトリを開き、次のいずれかを言う。

```
/daihon                    スキルを直接起動
テーマ提案して              → STEP1(5案を提示)
3番で                      → STEP2(素材台帳→ビート表→本文→監査)
〇〇について台本を書いて     → STEP2
ビート17と30が薄い。増築して → 増築モード
```

生成物は `output/<日付>_<テーマ短縮名>/` に4点保存される。

| ファイル | 内容 |
|---|---|
| `01_素材台帳.md` | 15行以上の実在素材。そのままファクトチェックリストになる |
| `02_ビート表.md` | 41ビートへの素材割り付け |
| `03_台本.txt` | 本文(プレーンテキスト。AI音声への入力そのもの) |
| `04_制作メモ.md` | タイトル案3・サムネ文言案3・概要欄・ファクトチェックリスト |

## 監査

台本を書いたら必ず機械監査を通す。**FAILが残っている状態で納品しない。**

```bash
python3 tools/audit.py output/<ディレクトリ>/03_台本.txt
python3 tools/audit.py output/<ディレクトリ>/03_台本.txt --verbose   # ビート別字数一覧
```

判定基準は `tools/beats.json`。目視でしか測れない項目は `.claude/skills/daihon/references/audit.md`。

## リポジトリ構成

```
.claude/skills/daihon/
  SKILL.md                    生成の全工程(STEP1/STEP2/増築モード)
  references/beats.md         41ビート設計図。構成と分量の唯一の正
  references/style.md         文体規律・密度の4技法・TTS表記ルール
  references/audit.md         目視チェック項目と増築の優先順位
tools/
  beats.json                  機械可読の仕様(字数・ビート・禁止記号)
  audit.py                    機械監査
  build_project_instructions.py  Claudeプロジェクト用の1枚指示書を生成
dist/
  project-instructions.md     上の生成物。Claude Projectの「指示」欄に貼る用
knowledge/
  reference-scripts/A〜D.md   高再生台本4本(自動文字起こし。文体参照のみ)
  sample/                     v2期のテスト台本(制作メモの形式参照のみ)
docs/                         原典(チャンネル分析・v3.1指示書・自己改善レポート)
output/                       生成物
```

## 絶対規律

- **実在の研究・統計のみを使う。存在が不確かな研究や数値の創作を固く禁じる。** チャンネルの生命線は信頼である
- 記憶が不確かな数値は「およそ」に留め、精密値を偽装しない
- 実在の個人・団体を悪玉にしない。犯人は常に「構造」に置く
- 参照台本A〜Dは自動文字起こしのため誤変換を含む。**数値・固有名詞をそこから引用しない**
- 確度「中」「要確認」の項目は、公開前検証が必要である旨を制作メモに明記する

## Claude Project でも使う場合

このリポジトリを開かずに Claude の Project 機能で運用したい場合:

```bash
python3 tools/build_project_instructions.py
```

`dist/project-instructions.md` が生成されるので、その全文を Project の「指示」欄に貼り、ナレッジに `knowledge/` 以下をアップロードする。ただし**機械監査 `tools/audit.py` は使えなくなる**ため、字数・ビートの担保は目視のみになる。
