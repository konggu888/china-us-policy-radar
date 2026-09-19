import json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
NEWS=DATA/'news.json'
ARCH=DATA/'archive'
ARCH.mkdir(parents=True, exist_ok=True)

def parse_time(n):
    s=str(n.get('time') or n.get('updated') or n.get('published') or '').strip()
    if not s:
        return None
    s=re.sub(r' UTC$','+00:00',s)
    try:
        return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:
        return None

try:
    news=json.loads(NEWS.read_text(encoding='utf-8'))
except Exception:
    news=[]

if not isinstance(news,list):
    news=[]

now=datetime.now(timezone.utc)
cut=now-timedelta(days=31)

# Recovery path: if upstream collection ever leaves news.json empty,
# restore the recent working set from the monthly archive before publishing.
if not news:
    recovered=[]
    for p in sorted(ARCH.glob('*.json'), reverse=True):
        try:
            rows=json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(rows,list):
            continue
        for n in rows:
            if not isinstance(n,dict):
                continue
            dt=parse_time(n)
            if dt is None or dt>=cut:
                recovered.append(n)
    seen=set()
    clean=[]
    for n in recovered:
        k=str(n.get('url') or '').strip() or re.sub(r'\s+',' ',str(n.get('title') or '').strip().lower())
        if k and k not in seen:
            seen.add(k)
            clean.append(n)
    news=clean

# Archive discovered items by calendar month, deduplicated by URL/title.
months={}
for n in news:
    if not isinstance(n,dict):
        continue
    dt=parse_time(n) or now
    months.setdefault(dt.strftime('%Y-%m'),[]).append(n)

for month,rows in months.items():
    p=ARCH/f'{month}.json'
    try:
        old=json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        old=[]
    if not isinstance(old,list):
        old=[]
    merged=old+rows
    seen=set()
    out=[]
    for n in merged:
        if not isinstance(n,dict):
            continue
        k=str(n.get('url') or '').strip() or re.sub(r'\s+',' ',str(n.get('title') or '').strip().lower())
        if k and k not in seen:
            seen.add(k)
            out.append(n)
    out.sort(key=lambda x:parse_time(x) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')

# Keep a 31-day working feed; archive remains the long-term source.
working=[n for n in news if isinstance(n,dict) and (parse_time(n) or now)>=cut]
working.sort(key=lambda n:parse_time(n) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
NEWS.write_text(json.dumps(working,ensure_ascii=False,indent=2),encoding='utf-8')
print('archive:',sum(len(v) for v in months.values()),'items across',len(months),'months; working feed:',len(working))
