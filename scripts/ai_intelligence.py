import json, os, re, sys, urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; NEWS=DATA/'news.json'; ARCH=DATA/'archive'; OUT=DATA/'ai_summaries.json'
KEY=os.getenv('DEEPSEEK_API_KEY','').strip(); MODEL=os.getenv('DEEPSEEK_MODEL','deepseek-v4-flash')
CATS=['政治','金融','经济','产业','科技 / AI','国防','内政','国家安全','外交','贸易 / 供应链','能源 / 资源','中美博弈','全球政策']

def load_news():
 rows=[]
 try: rows+=json.loads(NEWS.read_text(encoding='utf-8'))
 except Exception: pass
 if ARCH.exists():
  for p in ARCH.glob('*.json'):
   try: rows+=json.loads(p.read_text(encoding='utf-8'))
   except Exception: pass
 seen=set();out=[]
 for n in rows:
  k=n.get('url') or n.get('title')
  if k and k not in seen:seen.add(k);out.append(n)
 return out

def dt(n):
 s=n.get('time') or n.get('updated') or ''
 if not s:return None
 try:return datetime.fromisoformat(re.sub(r' UTC$','+00:00',s).replace('Z','+00:00')).astimezone(timezone.utc)
 except Exception:return None

def call(prompt,max_tokens=1800):
 if not KEY:return None
 body={'model':MODEL,'messages':[{'role':'system','content':'你是全球战略政策情报分析员。只根据提供的公开情报判断，不把推测写成事实；明确区分官方立场、媒体报道和分析判断。输出合法JSON。'},{'role':'user','content':prompt}],'stream':False,'max_tokens':max_tokens,'response_format':{'type':'json_object'}}
 req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(body,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json','User-Agent':'China-US-Global-Intelligence-Radar/AI-3.0'})
 try:
  raw=urllib.request.urlopen(req,timeout=120).read().decode('utf-8');return json.loads(json.loads(raw)['choices'][0]['message']['content'])
 except Exception as e: print('DeepSeek error:',type(e).__name__);return None

def classify(rows):
 # AI, not rules, is authoritative for the 13-category first-pass and risk first-pass.
 # Only already-AI-classified items are skipped, so each new item is assessed once.
 todo=[n for n in rows if not n.get('ai_category')][:15]
 if not todo:return 0
 evidence=[{'id':i,'title':n.get('titleZh') or n.get('title',''),'original':n.get('title',''),'region_hint':n.get('region'),'category_hint':n.get('cat'),'source':n.get('sourceOrg') or n.get('source'),'sourceTier':n.get('sourceTier'),'official':n.get('official',False),'url':n.get('url')} for i,n in enumerate(todo)]
 prompt='''对以下情报逐条做AI初筛。AI必须最终决定：category（13类中选1类）、risk（低/中/高/极高）、region（china/us/global）、importance（1-100）、action（是否明确政策/监管/军事/经济行动）、reason（不超过30字）。category_hint和region_hint只是采集程序提示，不得直接照抄；必须按标题、来源和语境独立判断。英文标题同时给titleZh。不要改变URL。输出{"items":[...]}。13类：'''+','.join(CATS)+'\n数据：'+json.dumps(evidence,ensure_ascii=False)
 ans=call(prompt,4200)
 if not ans or not isinstance(ans.get('items'),list):return 0
 changed=0
 for x in ans['items']:
  try:n=todo[int(x['id'])]
  except Exception:continue
  if x.get('category') in CATS:n['cat']=x['category'];n['ai_category']=x['category']
  if x.get('region') in ('china','us','global'):n['region']=x['region'];n['ai_region']=x['region']
  if x.get('risk') in ('低','中','高','极高'):n['risk']=x['risk'];n['ai_risk']=x['risk']
  if x.get('importance') is not None:n['ai_importance']=max(1,min(100,int(x['importance'])))
  n['ai_action']=bool(x.get('action',False));n['ai_reason']=str(x.get('reason',''))[:120]
  if x.get('titleZh'):n['titleZh']=str(x['titleZh'])[:240]
  changed+=1
 NEWS.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');return changed

def window_rows(rows,days):
 cut=datetime.now(timezone.utc)-timedelta(days=days);return [n for n in rows if (dt(n) or datetime.now(timezone.utc))>=cut]

def digest(rows,days):
 rs=window_rows(rows,days);cats=Counter(n.get('cat','全球政策') for n in rs);regs=Counter(n.get('region','global') for n in rs);risks=Counter(n.get('risk','低') for n in rs)
 top=sorted(rs,key=lambda n:(n.get('ai_importance',0),n.get('importance_score',0)),reverse=True)[:80]
 return {'count':len(rs),'categories':dict(cats),'regions':dict(regs),'risks':dict(risks),'top':[{'title':n.get('titleZh') or n.get('title'),'region':n.get('region'),'category':n.get('cat'),'risk':n.get('risk'),'importance':n.get('ai_importance',n.get('importance_score',0)),'source':n.get('sourceOrg') or n.get('source'),'url':n.get('url')} for n in top]}

def make_summary(rows,days,label,market):
 d=digest(rows,days)
 prompt=f'''请根据下面{label}公开情报做中文战略情报摘要。输出JSON字段：headline、executive_summary、china（正在做什么/对外政策/对内政策/重点板块）、us（正在做什么/对外政策/对内政策/重点板块）、global（全球正在发生什么/区域热点/主要政策方向）、us_market（上涨板块/下跌板块/观察依据）、key_risks、key_opportunities、signals_to_watch、confidence、evidence_count。不要预测具体事件概率，不要提供个股买卖建议；上涨/下跌板块只能引用给出的市场数据。区分事实、官方立场与分析判断。\n情报统计：{json.dumps(d,ensure_ascii=False)}\n美国板块市场数据：{json.dumps(market,ensure_ascii=False)}'''
 return call(prompt,4200)

def main():
 period=sys.argv[1] if len(sys.argv)>1 else 'daily';rows=load_news();classified=classify(rows);market={}
 try:market=json.loads((DATA/'market_sectors.json').read_text(encoding='utf-8'))
 except Exception:pass
 days={'daily':1,'weekly':7,'monthly':30,'quarterly':92,'half_year':180}.get(period,1)
 if not KEY:print('DEEPSEEK_API_KEY not configured; non-AI data pipeline remains active');return 0
 summary=make_summary(rows,days,period,market)
 if not summary:return 1
 try:allout=json.loads(OUT.read_text(encoding='utf-8'))
 except Exception:allout={}
 stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d');allout.setdefault(period,{})[stamp]={'period':period,'days':days,'generated_at':datetime.now(timezone.utc).isoformat(),'summary':summary,'evidence':digest(rows,days)}
 OUT.write_text(json.dumps(allout,ensure_ascii=False,indent=2),encoding='utf-8');print('DeepSeek',period,'summary generated; AI classified/risk-assessed',classified,'new items');return 0
if __name__=='__main__':sys.exit(main())