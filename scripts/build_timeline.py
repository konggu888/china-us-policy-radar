import json, re
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; NEWS=DATA/'news.json'; OUT=DATA/'timeline.json'
try: rows=json.loads(NEWS.read_text(encoding='utf-8'))
except Exception: rows=[]
def parse_time(n):
    s=str(n.get('time') or n.get('updated') or '')
    if not s:return datetime.min.replace(tzinfo=timezone.utc)
    try:return datetime.fromisoformat(re.sub(r' UTC$','+00:00',s).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return datetime.min.replace(tzinfo=timezone.utc)
def score(n):
    return ({'极高':4,'高':3,'中':2,'低':1}.get(n.get('risk'),0), n.get('importance_score',0), n.get('ai_importance',0))
# Prefer genuine global/multilateral events; fall back to the most important recent items
# when the global feed is temporarily sparse.
global_rows=[n for n in rows if n.get('region')=='global']
source=global_rows if len(global_rows)>=10 else sorted(rows,key=lambda n:(score(n),parse_time(n)),reverse=True)
source=sorted(source,key=lambda n:(score(n),parse_time(n)),reverse=True)
seen=set(); events=[]
for n in source:
    title=(n.get('titleZh') or n.get('title') or '').strip()
    url=n.get('url','')
    key=url or title
    if not title or key in seen:continue
    seen.add(key)
    events.append({'time':n.get('time') or n.get('updated') or '', 'title':title[:240], 'url':url, 'risk':n.get('ai_risk') or n.get('risk','低'), 'category':n.get('ai_category') or n.get('cat','全球政策'), 'region':n.get('ai_region') or n.get('region','global'), 'source':n.get('sourceOrg') or n.get('source',''), 'importance':n.get('ai_importance',n.get('importance_score',0))})
    if len(events)>=30:break
OUT.write_text(json.dumps({'updated':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'events':events},ensure_ascii=False,indent=2),encoding='utf-8')
print('timeline:',len(events),'events')