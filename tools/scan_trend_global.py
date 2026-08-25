import json, subprocess, sys, urllib.parse, os
from concurrent.futures import ThreadPoolExecutor

os.environ['SSL_CERT_FILE']='/root/.ccr/ca-bundle.crt'
os.environ['REQUESTS_CA_BUNDLE']='/root/.ccr/ca-bundle.crt'

# 今週アップ かつ 再生数順。何が今スパイクしているかを見る
SP = "CAMSBAgDEAE%3D"
QUERIES = ["なぜ","日本","話題","炎上","解説","理由","現実","真実","衝撃","論争",
           "問題","批判","値上げ","AI","若者","結婚","仕事","社会","事件","制度"]

def search(q):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}&sp={SP}"
    try:
        out = subprocess.run(["yt-dlp","--flat-playlist","-J","--playlist-end","40",url],
                             capture_output=True, timeout=240)
        return json.loads(out.stdout).get("entries") or []
    except Exception as e:
        print(f"  !! {q}: {e}", file=sys.stderr); return []

seen = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    for q, ents in zip(QUERIES, ex.map(search, QUERIES)):
        print(f"{q}: {len(ents)}", file=sys.stderr)
        for e in ents:
            if e.get("id"): seen.setdefault(e["id"], e)

rows = [e for e in seen.values() if (e.get("view_count") or 0) >= 100000]
rows.sort(key=lambda e: -(e.get("view_count") or 0))
json.dump(rows, open("trend.json","w"), ensure_ascii=False)
print(f"\n10万回以上 {len(rows)}本 / 収集 {len(seen)}本\n", file=sys.stderr)
for e in rows[:60]:
    print(f"{e['view_count']:>9,} {(e.get('duration') or 0)//60:>4}分 | {(e.get('channel') or '')[:16]:16s} | {(e.get('title') or '')[:58]}")
