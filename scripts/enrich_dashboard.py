import json, re, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'dashboard.json'; UA='China-US-Global-Intelligence-Radar/5.1'
def fetch_json(url):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':UA})
        with urllib.request.urlopen(req,timeout=15) as r:return json.loads(r.read())
    except Exception:return None
def market(symbol):
    obj=fetch_json('https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(symbol)+'?range=5d&interval=1d')
    try:
        res=obj['chart']['result'][0]; closes=[x for x in res['indicators']['quote'][0]['close'] if x is not None]; price=closes[-1]; prev=closes[-2] if len(closes)>1 else price
        return {'symbol':symbol,'value':round(price,4),'change_pct':round((price/prev-1)*100,2),'time':datetime.fromtimestamp(res['timestamp'][-1],timezone.utc).strftime('%Y-%m-%d')}
    except Exception:return {'symbol':symbol,'value':None,'change_pct':None,'time':''}
try: news=json.loads((DATA/'news.json').read_text(encoding='utf-8'))
except Exception: news=[]
now=datetime.now(timezone.utc); today=now.strftime('%Y-%m-%d')
# Standardized impact layer: heuristic triage, not a human analyst conclusion.
def enrich(n):
    t=(n.get('title','')+' '+n.get('cat','')).lower(); cat=n.get('cat','')
    inds=[]
    rules={'科技 / AI':['AI','artificial intelligence','chip','semiconductor','technology','机器人','人工智能','芯片','半导体'], '能源 / 资源':['energy','oil','gas','lng','power','能源','石油','天然气','电力','稀土'], '金融':['bank','rate','bond','currency','finance','央行','利率','债券','汇率','金融'], '贸易 / 供应链':['trade','tariff','export','import','supply','shipping','关税','贸易','出口','进口','供应链'], '产业':['manufacturing','industry','factory','automotive','制造业','产业','工厂','汽车'], '国防':['military','missile','navy','defense','军事','导弹','海军','国防'], '房地产/内需':['housing','property','real estate','consumption','住房','房地产','消费']}
    for k,terms in rules.items():
        if any(x.lower() in t for x in terms):inds.append(k)
    if not inds: inds=[cat or '宏观政策']
    high=n.get('risk') in ('高','极高'); comp=n.get('cat')=='中美博弈'
    n['impact_industry']=list(dict.fromkeys(inds))[:4]
    n['short_term']='关注市场预期、政策执行与相关行业价格/订单变化' if high else '主要观察政策落地和市场情绪变化'
    n['long_term']='观察产业链、资本流向、贸易结构与政策持续性' if (high or comp) else '观察后续政策是否形成连续措施'
    n['watch_data']=['官方后续文件','行业数据','价格/订单','企业公告']
    n['policy_level']='高优先级' if n.get('sourceType')=='official' and high else '常规跟踪'
    return n
news=[enrich(n) for n in news]; (DATA/'news.json').write_text(json.dumps(news,ensure_ascii=False,indent=2),encoding='utf-8')
markets=[('USD/CNY','CNY=X'),('上证指数','000001.SS'),('标普500','^GSPC'),('美国10年期收益率','^TNX'),('布伦特原油','BZ=F'),('黄金','GC=F'),('VIX','^VIX')]
market_rows=[]
for name,symbol in markets:
    x=market(symbol); x['name']=name; market_rows.append(x)
cats=['政治','金融','经济','产业','科技 / AI','国防','内政','国家安全','外交','贸易 / 供应链','能源 / 资源','中美博弈','全球政策']
def count_terms(items,terms):return sum(1 for n in items if any(t.lower() in (n.get('title','')+' '+n.get('cat','')).lower() for t in terms))
def direction(region):
    items=[n for n in news if n.get('region')==region]; return sorted([(c,sum(1 for n in items if n.get('cat')==c)) for c in cats if sum(1 for n in items if n.get('cat')==c)],key=lambda x:x[1],reverse=True)[:6]
china=[n for n in news if n.get('region')=='china']; us=[n for n in news if n.get('region')=='us']
open_terms=['开放','open','trade','贸易','外资','investment','出口','import','export','RCEP','自由贸易','globalization','global trade']; restrict_terms=['制裁','sanction','tariff','关税','export control','出口管制','实体清单','restriction','限制']
open_score=count_terms(news,open_terms); restrict_score=count_terms(news,restrict_terms); global_temp=round(max(0,min(100,50+(open_score-restrict_score)*2)))
focus=sorted(news,key=lambda n:({'极高':4,'高':3,'中':2,'低':1}.get(n.get('risk'),0),n.get('sourceType')=='official',n.get('time','')),reverse=True)[:8]
focus=[{'title':n.get('title',''),'url':n.get('url',''),'risk':n.get('risk',''),'category':n.get('cat',''),'region':n.get('region',''),'source':n.get('sourceOrg') or n.get('source',''),'verification':n.get('verification',''),'impact_industry':n.get('impact_industry',[])} for n in focus]
comparison=[]
for label,items in [('中国',china),('美国',us)]:
    counts=Counter(n.get('cat') for n in items); comparison.append({'side':label,'total':len(items),'top_categories':[{'name':k,'count':v} for k,v in counts.most_common(6)],'risk_high':sum(1 for n in items if n.get('risk') in ('高','极高'))})
# Policy language radar: keyword families that often indicate direction changes; frequency is descriptive only.
keywords={'稳增长':['稳增长','growth support','stimulus'],'扩大内需':['扩大内需','消费','domestic demand'],'人工智能':['人工智能','AI','artificial intelligence'],'产业升级':['产业升级','manufacturing','新质生产力'],'开放':['开放','外资','open','investment'],'安全':['国家安全','security','export control','制裁'],'贸易':['贸易','关税','tariff','trade']}
policy_language=[{'keyword':k,'count':count_terms(news,v)} for k,v in keywords.items()]
source_matrix=[{'name':n,'type':'官方一手'} for n in ['中国政府网','国家发改委','中国人民银行','金融监管总局','中国证监会','国家外汇局','工业和信息化部','科技部','国家能源局','商务部','海关总署','外交部','国防部','国家统计局','财政部']]
policy_chain={'steps':['政策原文','财政/金融支持','企业与行业行动','商品/价格/订单','海关/统计数据','效果验证'],'note':'系统先发现政策，再要求后续数据验证；不会把政策发布直接等同于政策效果。'}
obj={'updated':now.strftime('%Y-%m-%d %H:%M UTC'),'market':market_rows,'globalization_temperature':{'score':global_temp,'label':'开放信号偏强' if global_temp>=60 else '限制信号偏强' if global_temp<=40 else '冷热交织','method':'公开政策/贸易/投资/制裁/出口管制信号的相对温度；不是官方指标。'},'policy_direction':{'china':direction('china'),'us':direction('us'),'global':direction('global')},'policy_language':policy_language,'policy_source_matrix':source_matrix,'policy_chain':policy_chain,'policy_comparison':comparison,'today_focus':focus}
OUT.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8'); print('wrote',OUT)
