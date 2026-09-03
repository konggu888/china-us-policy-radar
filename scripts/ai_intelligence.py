import json, os, re, sys, urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; NEWS=DATA/'news.json'; ARCH=DATA/'archive'; OUT=DATA/'ai_summaries.json'; AI_HEALTH=DATA/'ai_health.json'
KEY=os.getenv('DEEPSEEK_API_KEY','').strip(); MODEL=os.getenv('DEEPSEEK_MODEL','deepseek-v4-flash')
CATS=['政治','金融','经济','产业','科技 / AI','国防','内政','国家安全','外交','贸易 / 供应链','能源 / 资源','中美博弈','全球政策']
AI_BATCH=120
STRATEGIC_TERMS=('制裁','关税','出口管制','芯片','半导体','人工智能','军方','军事','导弹','海军','国防','国家安全','央行','利率','金融','汇率','贸易','供应链','能源','石油','天然气','稀土','投资','财政','监管','法案','总统令','行政令','外交','台海','乌克兰','台湾','sanction','tariff','export control','chip','semiconductor','artificial intelligence','military','defense','security','central bank','rate','trade','supply chain','energy','oil','gas','rare earth','investment','regulation','executive order','diplomacy')

def load_current():
 try:return json.loads(NEWS.read_text(encoding='utf-8'))
 except Exception:return []

def load_news():
 rows=load_current()
 if ARCH.exists():
  for p in ARCH.glob('*.json'):
   try:rows+=json.loads(p.read_text(encoding='utf-8'))
   except Exception:pass
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
 body={'model':MODEL,'messages':[{'role':'system','content':'你是全球战略政策情报分析员。只根据提供的公开情报判断，不把推测写成事实；明确区分官方立场、媒体报道和分析判断。输出合法JSON。分类必须以事件实际主体和政策对象为准，绝不能因为新闻媒体来自哪个国家就改变事件归属。'},{'role':'user','content':prompt}],'stream':False,'max_tokens':max_tokens,'response_format':{'type':'json_object'}}
 req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(body,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json','User-Agent':'China-US-Global-Intelligence-Radar/AI-4.2'})
 try:
  raw=urllib.request.urlopen(req,timeout=120).read().decode('utf-8');return json.loads(json.loads(raw)['choices'][0]['message']['content'])
 except Exception as e: print('DeepSeek error:',type(e).__name__);return None

def ai_worth(n):
 text=((n.get('titleZh') or '')+' '+n.get('title','')+' '+str(n.get('cat',''))).lower();score=0;tier=n.get('sourceTier') or n.get('sourceType')
 if tier in ('官方','official'):score+=8
 elif tier in ('国际机构','institution'):score+=6
 elif tier in ('权威媒体','major_media'):score+=4
 elif tier in ('媒体','media','其他媒体'):score+=1
 if n.get('official'):score+=5
 if n.get('risk') in ('极高','高'):score+=7
 elif n.get('risk')=='中':score+=2
 if n.get('cat') in ('中美博弈','国防','国家安全','能源 / 资源','贸易 / 供应链','科技 / AI'):score+=4
 if any(t.lower() in text for t in STRATEGIC_TERMS):score+=4
 d=dt(n)
 if d:
  age=(datetime.now(timezone.utc)-d).total_seconds()/86400
  if age<=1:score+=5
  elif age<=3:score+=3
  elif age<=7:score+=1
 if n.get('importance_score',0)>=70:score+=4
 return score

def select_todo(rows):
 candidates=[n for n in rows if not n.get('ai_category') or n.get('ai_category') not in CATS]
 ranked=sorted(candidates,key=ai_worth,reverse=True)
 return [n for n in ranked if ai_worth(n)>=8][:AI_BATCH]

def classify(rows):
 todo=select_todo(rows)
 if not todo:
  return 0
 evidence=[{'id':i,'title':n.get('titleZh') or n.get('title',''),'original':n.get('title',''),'collector_region_hint':n.get('region'),'collector_category_hint':n.get('cat'),'source':n.get('sourceOrg') or n.get('source'),'sourceTier':n.get('sourceTier'),'official':n.get('official',False),'url':n.get('url')} for i,n in enumerate(todo)]
 prompt='''对以下情报逐条进行AI初筛。AI必须最终决定：category（13类中1类）、risk（低/中/高/极高）、region（china/us/global）、importance（1-100）、action（是否明确政策/监管/军事/财政/贸易/经济行动）、reason（不超过30字），英文标题同时给titleZh。\n\n核心要求：collector_region_hint和collector_category_hint只是采集提示，绝不是答案。region必须按事件实际主体、政策实施者、政策对象和主要影响地区判断，绝不能按媒体所在国家判断。\n例：美国政府出台对华芯片限制=us；中国政府回应美国限制=china；中美双方同时采取措施=global；中国媒体报道美国政策=us；美国媒体报道中国房地产=china；WTO/IMF/联合国/G20等国际制度或多国共同政策=global；单纯国际媒体报道某国事件不等于global。\ncategory与region独立：美联储降息=金融+us；WTO贸易规则=贸易 / 供应链或全球政策+global；中美关税互相加征=中美博弈+global。\n不要改变URL。输出{"items":[...]}。13类：'''+','.join(CATS)+'\n数据：'+json.dumps(evidence,ensure_ascii=False)
 ans=call(prompt,7000)
 if not ans or not isinstance(ans.get('items'),list):
  return 0
 changed=0
 for x in ans['items']:
  try:n=todo[int(x['id'])]
  except Exception:continue
  vc=x.get('category') in CATS; vr=x.get('region') in ('china','us','global'); vk=x.get('risk') in ('低','中','高','极高')
  if vc:n['cat']=x['category'];n['ai_category']=x['category']
  if vr:n['region']=x['region'];n['ai_region']=x['region']
  if vk:n['risk']=x['risk'];n['ai_risk']=x['risk']
  if x.get('importance') is not None:
   try:n['ai_importance']=max(1,min(100,int(x['importance'])))
   except Exception:pass
  n['ai_action']=bool(x.get('action',False));n['ai_reason']=str(x.get('reason',''))[:120]
  if x.get('titleZh'):n['titleZh']=str(x['titleZh'])[:240]
  if vc and vr and vk:changed+=1
 if changed:NEWS.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 return changed

def window_rows(rows,days):
 cut=datetime.now(timezone.utc)-timedelta(days=days);return [n for n in rows if (dt(n) or datetime.now(timezone.utc))>=cut]

def digest(rows,days):
 rs=window_rows(rows,days);cats=Counter(n.get('ai_category') or n.get('cat','全球政策') for n in rs);regs=Counter(n.get('ai_region') or n.get('region','global') for n in rs);risks=Counter(n.get('ai_risk') or n.get('risk','低') for n in rs)
 top=sorted(rs,key=lambda n:(n.get('ai_importance',0),n.get('importance_score',0)),reverse=True)[:80]
 return {'count':len(rs),'categories':dict(cats),'regions':dict(regs),'risks':dict(risks),'top':[{'title':n.get('titleZh') or n.get('title'),'region':n.get('ai_region') or n.get('region'),'category':n.get('ai_category') or n.get('cat'),'risk':n.get('ai_risk') or n.get('risk'),'importance':n.get('ai_importance',n.get('importance_score',0)),'source':n.get('sourceOrg') or n.get('source'),'url':n.get('url')} for n in top]}

def make_summary(rows,days,label,market):
 d=digest(rows,days)
 prompt=f'''请根据下面{label}公开情报做中文战略情报摘要。输出JSON字段：headline、executive_summary、china（正在做什么/对外政策/对内政策/重点板块）、us（正在做什么/对外政策/对内政策/重点板块）、global（全球正在发生什么/区域热点/主要政策方向）、us_market（上涨板块/下跌板块/观察依据）、a_share_market（上涨指数/下跌指数/观察依据）、key_risks、key_opportunities、signals_to_watch、confidence、evidence_count。不要预测具体事件概率，不要提供个股买卖建议；市场涨跌只能引用给出的市场数据。区分事实、官方立场与分析判断。\n情报统计：{json.dumps(d,ensure_ascii=False)}\n美股板块与A股市场数据：{json.dumps(market,ensure_ascii=False)}'''
 return call(prompt,4200)

def write_health(period,classified,summary_ok,reason=''):
 try:h=json.loads(AI_HEALTH.read_text(encoding='utf-8'))
 except Exception:h={}
 h.update({'updated':datetime.now(timezone.utc).isoformat(),'configured':bool(KEY),'model':MODEL,'last_period':period,'last_classified':classified,'last_summary_ok':summary_ok,'last_error':reason})
 h['total_ai_classified']=int(h.get('total_ai_classified',0))+classified
 AI_HEALTH.write_text(json.dumps(h,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
 period=sys.argv[1] if len(sys.argv)>1 else 'daily'
 current=load_current();classified=classify(current)
 if not KEY:
  write_health(period,0,False,'DEEPSEEK_API_KEY not configured')
  print('DEEPSEEK_API_KEY not configured; AI calls skipped')
  return 0
 if period=='classify':
  write_health(period,classified,True)
  print('DeepSeek classification run; new high-value items:',classified)
  return 0
 rows=load_news();market={}
 try:market=json.loads((DATA/'market_sectors.json').read_text(encoding='utf-8'))
 except Exception:pass
 days={'daily':1,'weekly':7,'monthly':30,'quarterly':92,'half_year':180}.get(period,1)
 summary=make_summary(rows,days,period,market)
 if not summary:
  write_health(period,classified,False,'summary API call failed')
  return 1
 try:allout=json.loads(OUT.read_text(encoding='utf-8'))
 except Exception:allout={}
 stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d');allout.setdefault(period,{})[stamp]={'period':period,'days':days,'generated_at':datetime.now(timezone.utc).isoformat(),'summary':summary,'evidence':digest(rows,days)}
 OUT.write_text(json.dumps(allout,ensure_ascii=False,indent=2),encoding='utf-8');write_health(period,classified,True);print('DeepSeek',period,'summary generated; AI classified/risk-assessed',classified,'new high-value items');return 0
if __name__=='__main__':sys.exit(main())