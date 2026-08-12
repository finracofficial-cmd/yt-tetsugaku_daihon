# 参照チャンネルの自動字幕(全93本)

参照チャンネル「考えすぎる葦」の全動画から、YouTubeの日本語自動字幕
(`ja-orig`)を取得し、解析用のプレーンテキストへ変換したもの。

## 取得と変換

```bash
pip install yt-dlp
export SSL_CERT_FILE=/root/.ccr/ca-bundle.crt

# 動画一覧
python3 -m yt_dlp --flat-playlist --extractor-args "youtube:lang=ja" \
  --print "%(id)s\t%(title)s" \
  "https://www.youtube.com/@kangaesugiruashi/videos" > index.tsv

# 字幕(1本ずつ。連続で叩くと止められるので2秒あける)
python3 -m yt_dlp --skip-download --write-auto-subs \
  --sub-langs "ja-orig" --sub-format json3 -o "%(id)s" \
  "https://www.youtube.com/watch?v=<videoId>"

# json3 → テキスト
python3 tools/subs_to_text.py knowledge/reference-scripts/auto
```

**以前「字幕トラックが無いので書き起こせない」と記録していたが、これは誤り
だった。** `/watch` のHTMLを直接読むと `captionTracks` が空に見えるだけで、
yt-dlp が InnerTube の android vr クライアント経由で叩けば普通に取得できる。

## ファイル

| | |
|---|---|
| `index.tsv` | videoId と日本語タイトルの対応表(93本) |
| `<videoId>.txt` | 1行目=タイトル / 2行目=URL / 空行 / 本文 |
| `<videoId>.ja-orig.json3` | 生の字幕。**1本500KBあるため版管理しない**(`.gitignore`) |

## 使うときの注意

- **これは自動音声認識であり、誤変換を含む。** 構造と話法の参照にのみ使い、
  **数値・固有名詞をここから引用してはならない**
- 手作業版(`../viral/*.txt`)より句読点が入っており質は高いが、規律は同じ
- `[音楽]` などのノイズ表記と、疑問符・感嘆符は変換時に除いてある
  (文分割を「。」に統一するため)

## 解析

```bash
python3 tools/analyze_refs.py knowledge/reference-scripts/auto
```
