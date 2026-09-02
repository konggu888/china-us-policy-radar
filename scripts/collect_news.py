import json, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'news.json'
HISTORY=ROOT/'data'/'history.json'
UA='China-US-Global-Intelligence-Radar/1.1'
QUERIES={
 'china':'China economy OR China military OR China security OR China policy',
 'us':'United States economy OR US military OR US security OR US policy',
 'global':'geopolitical risk OR global trade OR energy security OR conflict OR shipping',
 'competition':'China US trade OR China US technology OR China US sanctions OR Taiwan'
}
CATS=[('能源安全',r'energy|oil|gas|lng|pipeline|opec|electricity|power|uranium|nuclear|能源|石油|天然气|液化气|电力'),('军事',r'military|missile|navy|air force|army|defen[cs]e|warship|exercise|drone|weapon|军事|导弹|军舰|军演'),('安全',r'security|terror|cyber|border|intelligence|sanction|安全|网络攻击|制裁|边境'),('金融经济',r'economy|economic|market|stocks|inflation|interest rate|tariff|trade|gdp|bank|debt|金融|经济|关税|贸易|通胀'),('内政',r'election|congress|government|president|parliament|protest|domestic|policy|选举|国会|政府|总统|内政'),('中美竞争',r'china.?us|us.?china|beijing|washington|taiwan|semiconductor|chip|technology|中美|台海|芯片|半导体'),('全球化',r'globalization|global trade|supply chain|deglobal|全球化|供应链')]

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=20) as r:return r.read()

def clean(s):return re.sub(r'<[^>]+>|\s+',' ',s or '').strip()
def category(t):
    for name,p in CATS:
        if re.search(p,t,re.I):return name
    return '全球化'
def risk(t):
    if re.search(r'war|invasion|attack|missile|strike|blockade|nuclear|major sanction|重大冲突|战争|入侵|袭击|导弹|封锁|核',t,re.I):return '高'
    if re.search(r'tariff|sanction|military|security|election|energy|oil|taiwan|trade|制裁|军事|安全|选举|能源|台海|贸易',t,re.I):return '中'
    return '低'

def gdelt(q,region):
    params=urllib.parse.urlencode({'query':q,'mode':'artlist','maxrecords':'30','format':'json','timespan':'24h','sort':'HybridRel'})
    try:
        obj=json.loads(fetch('https://api.gdeltproject.org/api/v2/doc/doc?'+params))
        out=[]
        for a in obj.get('articles',[]):
            title=clean(a.get('title'))
            if not title:continue
            out.append({'title':title,'url':a.get('url'),'source':a.get('domain','GDELT'),'time':a.get('seendate','')[:10],'region':region,'cat':category(title),'risk':risk(title)})
        return out
    except Exception:return []

items=[]
for region,q in QUERIES.items(): items += gdelt(q,'global' if region=='competition' else region)
seen=set();uniq=[]
for x in items:
    key=re.sub(r'[^a-z0-9]','',x['title'].lower())
    if key and key not in seen: seen.add(key); uniq.append(x)
uniq=uniq[:160]
now=datetime.now(timezone.utc)
for i,x in enumerate(uniq):
    x['x']=8+(i*37)%84; x['y']=8+(i*61)%84; x['updated']=now.strftime('%Y-%m-%d %H:%M UTC')
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(uniq,ensure_ascii=False,indent=2),encoding='utf-8')

# Keep a compact 30-day daily trend for the dashboard.
counts=Counter(x['risk'] for x in uniq)
region_counts={r:sum(1 for x in uniq if x['region']==r) for r in ('china','us','global')}
entry={'date':now.strftime('%Y-%m-%d'),'total':len(uniq),'critical':counts.get('极高',0),'high':counts.get('高',0),'medium':counts.get('中',0),'low':counts.get('低',0),**{f'{r}_items':v for r,v in region_counts.items()}}
try: history=json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else []
except Exception: history=[]
history=[h for h in history if h.get('date')!=entry['date']]+[entry]
history=history[-30:]
HISTORY.write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'wrote {len(uniq)} items and {len(history)} history points')
