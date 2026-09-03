import json, os, re, sys, urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; NEWS=DATA/'news.json'; ARCH=DATA/'archive'; OUT=DATA/'ai_summaries.json'
KEY=os.getenv('DEEPSEEK_API_KEY','').strip(); MODEL=os.getenv('DEEPSEEK_MODEL','deepseek-v4-flash')
CATS=['政治','金融','经济','产业','科技 / AI','国防','内政','国家安全','外交','贸易 / 供应链','能源 / 资源','中美博弈','全球政策']

# Cost policy: use code for collection, dedupe, market math and obvious classification.
# DeepSeek is reserved for ambiguity resolution and strategic summaries. Default is V4-Flash
# with low reasoning effort; V4-Pro is intentionally not used in scheduled jobs.
KEYWORDS={
'科技 / AI':['ai','artificial intelligence','芯片','半导体','quantum','人工智能','算力','software','technology'],
'国防':['defense','defence','military','army','navy','air force','missile','武器','军方','国防','军事'],
'能源 / 资源':['energy','oil','gas','lng','nuclear','solar','能源','石油','天然气','核能','矿产','资源'],
'贸易 / 供应链':['tariff','trade','export','import','supply chain','customs','关税','贸易','出口','进口','供应链'],
'金融':['fed','federal reserve','treasury','interest rate','bank','finance','金融','央行','利率','财政'],
'经济':['gdp','inflation','employment','jobs','economic','economy','cpi','pmi','经济','通胀','就业','gdp'],
'外交':['state department','foreign minister','diplomatic','embassy','sanction','外交','使馆','制裁'],
'中美博弈':['china-us','u.s.-china','us-china','beijing washington','中美','美中'],
'政治':['president','election','congress','senate','parliament','presidential','总统','国会','议会','选举'],
'内政':['domestic policy','immigration','healthcare','education','housing','内政','移民','医疗','教育','住房'],
'国家安全':['national security','cybersecurity','intelligence','homeland security','国家安全','网络安全','情报'],
'产业':['industry','manufacturing','factory','industrial','制造业','产业'],
'全球政策':['united nations','imf','world bank','wto','oecd','global policy','联合国','全球政策']}

def load_news():
    rows=[]
    try: rows += json.loads(NEWS.read_text(encoding='utf-8'))
    except Exception: pass
    if ARCH.exists():
        for p in ARCH.glob('*.json'):
            try: rows += json.loads(p.read_text(encoding='utf-8'))
            except Exception: pass
    seen=set(); out=[]
    for n in rows:
        k=n.get('url') or n.get('title')
        if k and k not in seen:seen.add(k);out.append(n)
    return out

def dt(n):
    s=(n.get('time') or n.get('updated') or '')
    if not s:return None
    try:return datetime.fromisoformat(re.sub(r' UTC$','+00:00',s).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return None

def local_classify(n):
    text=((n.get('titleZh') or '')+' '+(n.get('title') or '')+' '+(n.get('sourceOrg') or '')).lower()
    hits=[]
    for cat,words in KEYWORDS.items():
        score=sum(1 for w in words if w.lower() in text)
        if score:hits.append((score,cat))
    if not hits:return None
    hits.sort(reverse=True)
    return hits[0][1] if hits[0][0]>=1 else None

def call(prompt,max_tokens=1800):
    if not KEY:return None
    body={'model':MODEL,'messages':[{'role':'system','content':'你是全球战略政策情报分析员。只根据提供的公开情报做归纳，不把推测写成事实；明确区分官方立场、媒体报道和分析判断。输出必须是合法JSON。'}, {'role':'user','content':prompt}], 'stream':False,'max_tokens':max_tokens,'response_format':{'type':'json_object'},'thinking':{'type':'disabled'}}
    # Some deployments reject the optional thinking field; retry once without it.
    def req_body(b):
        req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(b,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json','User-Agent':'China-US-Global-Intelligence-Radar/DeepSeek-Cost-Optimized-2.0'})
        raw=urllib.request.urlopen(req,timeout=120).read().decode('utf-8'); obj=json.loads(raw); return json.loads(obj['choices'][0]['message']['content'])
    try:return req_body(body)
    except Exception:
        body.pop('thinking',None)
        try:return req_body(body)
        except Exception as e: print('DeepSeek error:',type(e).__name__); return None

def classify(rows):
    # First classify obvious cases locally. Only ambiguous high-value items consume API tokens.
    ambiguous=[]; changed=0
    for n in rows:
        if n.get('ai_category'):continue
        cat=local_classify(n)
        if cat:
            n['cat']=cat; n['ai_category']='local'; changed+=1
        else:
            ambiguous.append(n)
    todo=[n for n in ambiguous if (n.get('risk') in ('高','严重') or n.get('importance_level') in ('S','A') or n.get('importance_score',0)>=70)][:15]
    if not todo:
        NEWS.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8'); return changed
    evidence=[{'id':i,'title':n.get('titleZh') or n.get('title',''),'region':n.get('region'),'category':n.get('cat'),'source':n.get('sourceOrg') or n.get('source'),'risk':n.get('risk'),'url':n.get('url')} for i,n in enumerate(todo)]
    prompt='只处理这些高价值且分类不明确的情报。每条从13类选1类，并判断region为china/us/global，importance为1-100，是否明确政策行动action；给不超过20字reason。英文标题需要titleZh。输出 {"items":[...]}. 13类：'+','.join(CATS)+'\n数据：'+json.dumps(evidence,ensure_ascii=False)
    ans=call(prompt,2600)
    if ans and isinstance(ans.get('items'),list):
        for x in ans['items']:
            try:n=todo[int(x['id'])]
            except Exception:continue
            if x.get('category') in CATS:n['cat']=x['category'];n['ai_category']=x['category']
            if x.get('region') in ('china','us','global'):n['region']=x['region'];n['ai_region']=x['region']
            if x.get('importance') is not None:n['ai_importance']=max(1,min(100,int(x['importance'])))
            n['ai_action']=bool(x.get('action',False)); n['ai_reason']=str(x.get('reason',''))[:80]
            if x.get('titleZh'):n['titleZh']=str(x['titleZh'])[:240]
            changed+=1
    NEWS.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8'); return changed

def window_rows(rows,days):
    cut=datetime.now(timezone.utc)-timedelta(days=days)
    return [n for n in rows if (dt(n) or datetime.now(timezone.utc))>=cut]

def digest(rows,days):
    rs=window_rows(rows,days)
    cats=Counter(n.get('cat','全球政策') for n in rs); regs=Counter(n.get('region','global') for n in rs); levels=Counter(n.get('importance_level','C') for n in rs)
    # Send only compact evidence: enough for analysis, not the entire archive.
    top=sorted(rs,key=lambda n:(n.get('ai_importance',0),n.get('importance_score',0)),reverse=True)[:80]
    return {'count':len(rs),'categories':dict(cats),'regions':dict(regs),'importance_levels':dict(levels),'top':[{'title':n.get('titleZh') or n.get('title'),'region':n.get('region'),'category':n.get('cat'),'importance':n.get('ai_importance',n.get('importance_score',0)),'risk':n.get('risk'),'source':n.get('sourceOrg') or n.get('source'),'url':n.get('url')} for n in top]}

def make_summary(rows,days,label,market):
    d=digest(rows,days)
    prompt=f'''请根据下面{label}公开情报做中文战略情报摘要。输出JSON字段：headline、executive_summary、china（正在做什么/对外政策/对内政策/重点板块）、us（正在做什么/对外政策/对内政策/重点板块）、global（全球正在发生什么/区域热点/主要政策方向）、us_market（上涨板块/下跌板块/观察依据）、key_risks、key_opportunities、signals_to_watch、confidence、evidence_count。不要预测具体事件概率，不要提供个股买卖建议；上涨/下跌板块只能引用给出的市场数据。区分事实、官方立场与分析判断。\n情报统计：{json.dumps(d,ensure_ascii=False)}\n美国板块市场数据：{json.dumps(market,ensure_ascii=False)}'''
    return call(prompt,4200)

def main():
    period=sys.argv[1] if len(sys.argv)>1 else 'daily'
    rows=load_news(); classified=classify(rows)
    market={}
    try:market=json.loads((DATA/'market_sectors.json').read_text(encoding='utf-8'))
    except Exception:pass
    days={'daily':1,'weekly':7,'monthly':30,'quarterly':92,'half_year':180}.get(period,1)
    if not KEY:
        print('DEEPSEEK_API_KEY not configured; non-AI data pipeline remains active'); return 0
    summary=make_summary(rows,days,period,market)
    if not summary:return 1
    try:allout=json.loads(OUT.read_text(encoding='utf-8'))
    except Exception:allout={}
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d')
    allout.setdefault(period,{})[stamp]={'period':period,'days':days,'generated_at':datetime.now(timezone.utc).isoformat(),'summary':summary,'evidence':digest(rows,days)}
    OUT.write_text(json.dumps(allout,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DeepSeek',period,'summary generated; AI/ambiguous classifications processed',classified)
    return 0
if __name__=='__main__':sys.exit(main())
