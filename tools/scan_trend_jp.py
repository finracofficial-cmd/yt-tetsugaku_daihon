import json, subprocess, sys, urllib.parse, os, re
from concurrent.futures import ThreadPoolExecutor

os.environ['SSL_CERT_FILE']='/root/.ccr/ca-bundle.crt'
os.environ['REQUESTS_CA_BUNDLE']='/root/.ccr/ca-bundle.crt'
SP = "CAMSBAgDEAE%3D"   # 今週アップ × 再生数順

QUERIES = ["なぜ 日本","日本 なぜ 解説","話題 解説 日本","日本人 なぜ","日本 社会 問題",
           "AI 仕事 なぜ","AI バブル 解説","物価 なぜ 日本","円安 なぜ 解説","若者 なぜ 日本",
           "結婚 しない なぜ","日本語 なぜ","働き方 なぜ 日本","子育て なぜ 日本","孤独 日本 なぜ",
           "SNS なぜ 解説","スマホ 脳 解説","日本 教育 なぜ","男女 なぜ 日本","老後 なぜ 日本"]

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

JP = re.compile(r'[ぁ-んァ-ヶ一-龥]')
rows = [e for e in seen.values()
        if (e.get("view_count") or 0) >= 50000
        and len(JP.findall(e.get("title") or "")) >= 6
        and (e.get("duration") or 0) >= 300]
rows.sort(key=lambda e: -(e.get("view_count") or 0))
json.dump(rows, open("trend2.json","w"), ensure_ascii=False)
print(f"\n日本語・5分以上・5万回以上 = {len(rows)}本 / 収集 {len(seen)}本\n", file=sys.stderr)
for e in rows[:55]:
    print(f"{e['view_count']:>9,} {(e.get('duration') or 0)//60:>3}分 | {(e.get('channel') or '')[:14]:14s} | {(e.get('title') or '')[:58]}")
