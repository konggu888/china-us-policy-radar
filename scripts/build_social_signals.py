import json,re,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'social_signals.json'
UA='China-US-Global-Intelligence-Radar/SocialSignals-1.0'
QUERIES=[
 ('china','中国 就业 消费 房价 收入 体感 网友 评论 讨论','zh-CN','CN'),
 ('china','中国 经济 政策 网友 反应 评论 消费 就业','zh-CN','CN'),
 ('us','US economy jobs inflation housing consumer sentiment reactions comments','en-US','US'),
 ('global','geopolitics China US trade reactions public opinion comments','en-US','US')
]
def fetch(url):
 r=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml,application/xml,text/xml,*/*'})
 return urllib.request.urlopen(r,timeout=20).read()
def parse(raw,source,region):
 try: root=ET.fromstring(raw)
 except Exception:return []
 out=[]
 for n in root.findall('.//item')[:50]:
  t=(n.findtext('title') or '').strip(); u=(n.findtext('link') or '').strip(); d=(n.findtext('pubDate') or '').strip()
  if t and u: out.append({'title':re.sub(r'\\s+',' ',t)[:240],'url':u,'source':source,'region':region,'time':d})
 return out
rows=[]; health={}
for region,q,lang,country in QUERIES:
 url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':lang,'gl':country,'ceid':country+':en'})
 try:
  got=parse(fetch(url),'Google News discussion proxy',region); rows+=got; health[region]={'status':'ok','count':len(got)}
 except Exception as e: health[region]={'status':'error:'+type(e).__name__,'count':0}
seen=set(); uniq=[]
for x in rows:
 k=x['url'] or x['title']
 if k not in seen: seen.add(k); uniq.append(x)
# This layer is intentionally a discussion-signal proxy, not a representative public-opinion poll.
themes={
 '就业/收入':r'就业|工资|薪资|失业|job|employment|wage|income|layoff|unemployment',
 '住房/房价':r'房价|房地产|住房|mortgage|housing|home price|property',
 '物价/生活成本':r'物价|通胀|生活成本|inflation|cost of living|price',
 '消费':r'消费|零售|consumer|spending|retail',
 '贸易/关税':r'关税|贸易战|tariff|trade war|trade',
 '地缘安全':r'战争|冲突|制裁|军事|台海|war|conflict|sanction|military|security'
}
counts={k:0 for k in themes}
for x in uniq:
 for k,p in themes.items():
  if re.search(p,x['title'],re.I): counts[k]+=1
stamp=datetime.now(timezone.utc).isoformat()
OUT.write_text(json.dumps({'updated':stamp,'method':'public discussion discovery proxy via indexed public RSS; not representative survey data','items':uniq[:300],'theme_counts':counts,'health':health,'limitations':['搜索结果与媒体标题存在选择偏差','不能代表总体民意','未把单条评论当作总体态度','需后续接入有明确授权的公开评论数据源'],'status':'signal_only'},ensure_ascii=False,indent=2),encoding='utf-8')
print('social signals:',len(uniq),counts)
