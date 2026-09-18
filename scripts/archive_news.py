import json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; NEWS=DATA/'news.json'; ARCH=DATA/'archive'
ARCH.mkdir(parents=True,exist_ok=True)
try: news=json.loads(NEWS.read_text(encoding='utf-8'))
except Exception: news=[]
# If an upstream job left the working feed empty, rebuild it from the immutable monthly archive.
if not news:
    recovered=[]
    cutoff=datetime.now(timezone.utc)-timedelta(days=31)
    for p in sorted(ARCH.glob('*.json'),reverse=True):
        try: rows=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        for n in rows:
            t=None
            s=str(n.get('time') or n.get('updated') or '')
            try: t=datetime.fromisoformat(re.sub(r' UTC

def parse_time(n):
    s=(n.get('time') or n.get('updated') or '')
    if not s:return None
    s=re.sub(r' UTC$','+00:00',s)
    try:return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return None
now=datetime.now(timezone.utc)
# Archive every discovered item into monthly immutable-ish snapshots, deduped by URL/title.
months={}
for n in news:
    dt=parse_time(n) or now
    months.setdefault(dt.strftime('%Y-%m'),[]).append(n)
for month,rows in months.items():
    p=ARCH/f'{month}.json'
    try:old=json.loads(p.read_text(encoding='utf-8'))
    except Exception:old=[]
    merged=old+rows; seen=set(); out=[]
    for n in merged:
        k=(n.get('url') or '').strip() or re.sub(r'\s+',' ',n.get('title','').strip().lower())
        if k and k not in seen:seen.add(k);out.append(n)
    out.sort(key=lambda x:parse_time(x) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
# Keep a generous 30-day working feed for the UI. Long-term analysis uses archive, so nothing is lost.
cut=now-timedelta(days=31)
working=[n for n in news if (parse_time(n) or now)>=cut]
working.sort(key=lambda n:parse_time(n) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)
NEWS.write_text(json.dumps(working,ensure_ascii=False,indent=2),encoding='utf-8')
print('archive:',sum(len(v) for v in months.values()),'items across',len(months),'months; working feed:',len(working))
,'+00:00',s).replace('Z','+00:00')).astimezone(timezone.utc)
            except Exception: pass
            if t is None or t>=cutoff: recovered.append(n)
    seen=set(); news=[n for n in recovered if (n.get('url') or n.get('title')) and not ((n.get('url') or n.get('title')) in seen and seen.add(n.get('url') or n.get('title')))]


def parse_time(n):
    s=(n.get('time') or n.get('updated') or '')
    if not s:return None
    s=re.sub(r' UTC$','+00:00',s)
    try:return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return None
now=datetime.now(timezone.utc)
# Archive every discovered item into monthly immutable-ish snapshots, deduped by URL/title.
months={}
for n in news:
    dt=parse_time(n) or now
    months.setdefault(dt.strftime('%Y-%m'),[]).append(n)
for month,rows in months.items():
    p=ARCH/f'{month}.json'
    try:old=json.loads(p.read_text(encoding='utf-8'))
    except Exception:old=[]
    merged=old+rows; seen=set(); out=[]
    for n in merged:
        k=(n.get('url') or '').strip() or re.sub(r'\s+',' ',n.get('title','').strip().lower())
        if k and k not in seen:seen.add(k);out.append(n)
    out.sort(key=lambda x:parse_time(x) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
# Keep a generous 30-day working feed for the UI. Long-term analysis uses archive, so nothing is lost.
cut=now-timedelta(days=31)
working=[n for n in news if (parse_time(n) or now)>=cut]
working.sort(key=lambda n:parse_time(n) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)
NEWS.write_text(json.dumps(working,ensure_ascii=False,indent=2),encoding='utf-8')
print('archive:',sum(len(v) for v in months.values()),'items across',len(months),'months; working feed:',len(working))
