import json, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'dashboard.json'
UA='China-US-Global-Intelligence-Radar/5.0'

def fetch_json(url):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':UA})
        with urllib.request.urlopen(req,timeout=15) as r: return json.loads(r.read())
    except Exception: return None

def market(symbol):
    url='https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(symbol)+'?range=5d&interval=1d'
    obj=fetch_json(url)
    try:
        res=obj['chart']['result'][0]; meta=res['meta']; closes=[x for x in res['indicators']['quote'][0]['close'] if x is not None]
        price=closes[-1]; prev=closes[-2] if len(closes)>1 else price
        return {'symbol':symbol,'value':round(price,4),'change_pct':round((price/prev-1)*100,2),'time':datetime.fromtimestamp(res['timestamp'][-1],timezone.utc).strftime('%Y-%m-%d')}
    except Exception:return {'symbol':symbol,'value':None,'change_pct':None,'time':''}

try: news=json.loads((DATA/'news.json').read_text(encoding='utf-8'))
except Exception: news=[]
now=datetime.now(timezone.utc); today=now.strftime('%Y-%m-%d')
markets=[('USD/CNY','CNY=X'),('上证指数','000001.SS'),('标普500','^GSPC'),('美国10年期收益率','^TNX'),('布伦特原油','BZ=F'),('黄金','GC=F'),('VIX','^VIX')]
market_rows=[]
for name,symbol in markets:
    x=market(symbol); x['name']=name; market_rows.append(x)

cats=['政治','金融','经济','产业','科技 / AI','国防','内政','国家安全','外交','贸易 / 供应链','能源 / 资源','中美博弈','全球政策']
def count_terms(items, terms): return sum(1 for n in items if any(t.lower() in (n.get('title','')+' '+n.get('cat','')).lower() for t in terms))

def direction(region):
    items=[n for n in news if n.get('region')==region]
    scores=[]
    for c in cats:
        v=sum(1 for n in items if n.get('cat')==c)
        if v: scores.append((c,v))
    return sorted(scores,key=lambda x:x[1],reverse=True)[:6]

china= [n for n in news if n.get('region')=='china']; us=[n for n in news if n.get('region')=='us']; global_items=[n for n in news if n.get('region')=='global']
open_terms=['开放','open','trade','贸易','外资','investment','出口','import','export','RCEP','自由贸易','globalization','global trade']
restrict_terms=['制裁','sanction','tariff','关税','export control','出口管制','实体清单','restriction','限制']
open_score=count_terms(news,open_terms); restrict_score=count_terms(news,restrict_terms)
global_temp=round(max(0,min(100,50 + (open_score-restrict_score)*2)))

focus=sorted(news,key=lambda n: ({'极高':4,'高':3,'中':2,'低':1}.get(n.get('risk'),0), n.get('sourceType')=='official', n.get('time','')),reverse=True)[:8]
focus=[{'title':n.get('title',''),'url':n.get('url',''),'risk':n.get('risk',''),'category':n.get('cat',''),'region':n.get('region',''),'source':n.get('sourceOrg') or n.get('source',''),'verification':n.get('verification','')} for n in focus]

# Policy comparison is deliberately descriptive: it measures the mix of collected public signals, not policy quality or intent.
comparison=[]
for label,items in [('中国',china),('美国',us)]:
    counts=Counter(n.get('cat') for n in items)
    comparison.append({'side':label,'total':len(items),'top_categories':[{'name':k,'count':v} for k,v in counts.most_common(6)],'risk_high':sum(1 for n in items if n.get('risk') in ('高','极高'))})

obj={'updated':now.strftime('%Y-%m-%d %H:%M UTC'),'market':market_rows,'globalization_temperature':{'score':global_temp,'label':'开放信号偏强' if global_temp>=60 else '限制信号偏强' if global_temp<=40 else '冷热交织','method':'公开政策/贸易/投资/制裁/出口管制信号的相对温度；不是官方指标。'},'policy_direction':{'china':direction('china'),'us':direction('us'),'global':direction('global')},'policy_comparison':comparison,'today_focus':focus}
OUT.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
print('wrote',OUT)
