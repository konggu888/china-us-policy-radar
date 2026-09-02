import json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; NEWS=DATA/'news.json'; DASH=DATA/'dashboard.json'
try: news=json.loads(NEWS.read_text(encoding='utf-8'))
except Exception: news=[]
RISK={'极高':35,'高':26,'中':14,'低':5}
STRATEGIC={'中美博弈':22,'国防':18,'国家安全':18,'外交':15,'能源 / 资源':14,'贸易 / 供应链':14,'金融':12,'政治':11,'科技 / AI':11,'经济':10,'产业':9,'内政':8,'全球政策':8}
ACTION=re.compile(r'批准|通过|签署|发布|实施|生效|限制|制裁|关税|禁令|出口管制|军演|部署|撤军|谈判|协议|法案|任命|降息|加息|预算|投资|补贴|approved|signed|impose|sanction|tariff|ban|export control|deploy|exercise|agreement|bill|appoint|rate cut|rate hike|budget|subsid',re.I)
IMPACT=re.compile(r'供应链|半导体|芯片|能源|石油|天然气|金融市场|利率|汇率|美元|贸易|关税|军费|军事|核|台海|乌克兰|中东|AI|人工智能|稀土|关键矿产|supply chain|semiconductor|energy|oil|gas|rate|currency|trade|tariff|military|nuclear|Taiwan|Ukraine|Middle East|AI|critical minerals',re.I)

def importance(n):
 t=(n.get('title','')+' '+n.get('titleZh','')).strip(); cat=n.get('cat',''); s=RISK.get(n.get('risk'),0)+STRATEGIC.get(cat,6)
 if n.get('sourceType')=='official': s+=18
 elif n.get('sourceType')=='institution': s+=15
 elif n.get('sourceType')=='major_media': s+=8
 if ACTION.search(t): s+=12
 if IMPACT.search(t): s+=10
 if n.get('verification') in ('双源交叉','多源交叉'): s+=8
 s=min(100,s)
 if s>=78: level='S'
 elif s>=60: level='A'
 elif s>=40: level='B'
 else: level='C'
 reasons=[]
 if n.get('risk') in ('极高','高'): reasons.append('风险信号较强')
 if cat in ('中美博弈','国防','国家安全','外交','能源 / 资源','贸易 / 供应链'): reasons.append('涉及战略安全或关键链条')
 if ACTION.search(t): reasons.append('包含明确政策/行动信号')
 if IMPACT.search(t): reasons.append('可能影响市场、产业或供应链')
 if n.get('sourceType') in ('official','institution'): reasons.append('一手/机构来源优先')
 n['importance_score']=s; n['importance_level']=level; n['importance_reason']='；'.join(reasons[:3]) or '常规信息跟踪'
 return n
for n in news: importance(n)
# Event grouping: stable thematic buckets so the UI can expose the underlying articles.
def event_group(n):
 t=(n.get('title','')+' '+n.get('titleZh','')).lower()
 rules=[('台海 / 半导体',[r'taiwan',r'台海',r'semiconductor',r'chip',r'半导体',r'芯片']),('贸易 / 制裁',[r'tariff',r'trade',r'贸易',r'关税',r'sanction',r'制裁',r'export control',r'出口管制']),('军事 / 国防',[r'military',r'missile',r'navy',r'warship',r'军事',r'导弹',r'军舰',r'军演']),('能源 / 航运',[r'oil',r'gas',r'lng',r'energy',r'energy security',r'石油',r'天然气',r'能源',r'航运']),('金融 / 货币',[r'rate',r'fed',r'central bank',r'bond',r'currency',r'利率',r'美联储',r'央行',r'债券',r'汇率']),('宏观政策',[r'economy',r'gdp',r'inflation',r'budget',r'election',r'economy',r'经济',r'gdp',r'通胀',r'预算',r'选举'])]
 for name,ps in rules:
  if any(re.search(p,t,re.I) for p in ps): return name
 return '全球政策 / 其他'
for n in news:n['event_group']=event_group(n)
NEWS.write_text(json.dumps(news,ensure_ascii=False,indent=2),encoding='utf-8')
try: dash=json.loads(DASH.read_text(encoding='utf-8'))
except Exception: dash={}
rank=sorted(news,key=lambda n:(n.get('importance_score',0),n.get('risk') in ('极高','高'),n.get('time','')),reverse=True)
focus=[{'title':n.get('title',''),'titleZh':n.get('titleZh',''),'url':n.get('url',''),'risk':n.get('risk',''),'category':n.get('cat',''),'region':n.get('region',''),'source':n.get('sourceOrg') or n.get('source',''),'verification':n.get('verification',''),'impact_industry':n.get('impact_industry',[]),'importance_score':n.get('importance_score',0),'importance_level':n.get('importance_level','C'),'importance_reason':n.get('importance_reason','')} for n in rank if n.get('importance_score',0)>=55][:8]
dash['today_focus']=focus
dash['focus_method']='重要度排序：风险 + 战略领域 + 政策行动 + 潜在产业/市场影响 + 来源层级/交叉验证；不是简单按最新时间排序。'
dash['importance_method']='系统启发式重要度，不替代人工分析；S/A/B/C分别代表高优先级、重要、值得跟踪、常规。'
DASH.write_text(json.dumps(dash,ensure_ascii=False,indent=2),encoding='utf-8')
print('priority enriched',len(news),'items; focus',len(focus))
