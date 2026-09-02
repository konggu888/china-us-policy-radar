import json,re,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'news.json'; HEALTH=DATA/'collection_health.json'
UA='China-US-Global-Intelligence-Radar/BroadCollector-2.0'
CATS={'政治':'president election congress parliament government politics cabinet political 选举 总统 国会 政府 政治 内阁','金融':'central bank interest rate bond currency stocks banking finance monetary 美联储 央行 利率 债券 汇率 股市 金融','经济':'economy economic GDP inflation employment growth recession fiscal 经济 GDP 通胀 就业 增长 衰退 财政','产业':'industry manufacturing factory automotive steel industrial 产业 制造业 工厂 汽车 钢铁','科技 / AI':'AI artificial intelligence semiconductor chip technology quantum cloud robotics 科技 人工智能 半导体 芯片 量子 机器人','国防':'military defense missile navy air force army warship exercise drone weapon 国防 军事 导弹 海军 空军 军演 武器','内政':'domestic immigration border crime healthcare housing education protest 内政 移民 边境 治安 医疗 住房 教育 抗议','国家安全':'national security cyber intelligence espionage critical infrastructure security 国家安全 网络 情报 间谍 关键基础设施 安全','外交':'diplomacy diplomatic foreign ministry ambassador summit alliance NATO treaty 外交 大使 峰会 联盟 北约 条约','贸易 / 供应链':'trade tariff export import supply chain shipping logistics trade war 贸易 关税 出口 进口 供应链 航运 物流','能源 / 资源':'energy oil gas LNG pipeline OPEC electricity power uranium rare earth critical minerals 能源 石油 天然气 液化天然气 管道 电力 铀 稀土','中美博弈':'China US US China Taiwan export control sanctions semiconductor trade 中美 台海 出口管制 制裁 半导体','全球政策':'global policy international policy United Nations WTO global governance climate policy sanctions 全球政策 国际政策 联合国 全球治理 气候政策 制裁'}
MEDIA={'reuters.com':'权威媒体','apnews.com':'权威媒体','ft.com':'权威媒体','bloomberg.com':'权威媒体','wsj.com':'权威媒体','nytimes.com':'权威媒体','washingtonpost.com':'权威媒体','scmp.com':'权威媒体','nikkei.com':'权威媒体','afp.com':'权威媒体','xinhuanet.com':'权威媒体','people.com.cn':'权威媒体'}
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/xml, text/xml, */*'})
 with urllib.request.urlopen(req,timeout=15) as r:return r.read()
def domain(url):return urllib.parse.urlparse(url).netloc.lower().removeprefix('www.')
def risk(t):
 if re.search(r'war|attack|strike|missile|blockade|nuclear|invasion|战争|袭击|导弹|封锁|核|入侵',t,re.I):return '高'
 if re.search(r'sanction|tariff|military|security|energy|oil|trade|election|制裁|关税|军事|安全|能源|石油|贸易|选举',t,re.I):return '中'
 return '低'
def rss(query,region,cat,lang='en-US',gl='US'):
 url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':lang,'gl':gl,'ceid':gl+':en'})
 try: root=ET.fromstring(fetch(url))
 except Exception as e:return [],f'error:{type(e).__name__}'
 out=[]
 for item in root.findall('.//item')[:12]:
  title=(item.findtext('title') or '').strip(); link=(item.findtext('link') or '').strip(); pub=(item.findtext('pubDate') or '').strip()
  if not title or not link:continue
  m=re.search(r'\s+-\s+([^\-]+)$',title); source=m.group(1).strip() if m else domain(link); clean=re.sub(r'\s+-\s+[^\-]+$','',title).strip(); d=domain(link); tier=MEDIA.get(d,'其他媒体'); st='major_media' if tier=='权威媒体' else 'media'
  out.append({'title':clean[:220],'url':link,'source':source,'sourceType':st,'sourceOrg':source,'sourceTier':tier,'official':False,'verification':'单一来源','time':pub,'region':region,'cat':cat,'risk':risk(clean),'x':50,'y':50})
 return out,'ok'
queries=[]
for cat,terms in CATS.items():
 for region,prefix,lang,gl in [('china','China','en-US','US'),('us','United States','en-US','US'),('global','','en-US','US')]: queries.append((region,(prefix+' '+terms) if prefix else terms,cat,lang,gl))
for cat,terms in CATS.items(): queries.append(('china','中国 '+terms,cat,'zh-CN','CN'))
items=[]; health={}; total=0
for region,q,cat,lang,gl in queries:
 got,status=rss(q,region,cat,lang,gl); items+=got; total+=len(got); health[f'GoogleNews:{region}:{cat}:{lang}']={'method':'public_rss_discovery','status':status,'count':len(got)}
try: old=json.loads(OUT.read_text(encoding='utf-8'))
except Exception:old=[]
items+=old
seen=set(); uniq=[]
for x in items:
 k=re.sub(r'[^a-z0-9]','',x.get('url','').lower()) or re.sub(r'[^a-z0-9]','',x.get('title','').lower())
 if k and k not in seen: seen.add(k); uniq.append(x)
bad=('skip to main content','read more','learn more','view all','home','menu','search','subscribe','privacy','terms')
uniq=[x for x in uniq if len(x.get('title',''))>=18 and x.get('title','').strip().lower() not in bad]
now=datetime.now(timezone.utc); stamp=now.strftime('%Y-%m-%d %H:%M UTC')
for i,x in enumerate(uniq): x['updated']=stamp; x['x']=8+(i*37)%84; x['y']=8+(i*61)%84
# Balance the rolling feed: retain up to 60 recent/discovered items per region and 25 per category, then fill remaining slots by importance-independent recency.
by_region={r:[x for x in uniq if x.get('region')==r] for r in ('china','us','global')}
selected=[]; selected_keys=set()
for r in ('china','us','global'):
 for x in by_region[r][:180]:
  if x['url'] not in selected_keys and len([z for z in selected if z.get('region')==r])<180: selected.append(x); selected_keys.add(x['url'])
# Ensure every category exists in the retained set.
for cat in CATS:
 pool=[x for x in uniq if x.get('cat')==cat]
 have=sum(1 for x in selected if x.get('cat')==cat)
 for x in pool[:max(0,25-have)]:
  if x['url'] not in selected_keys: selected.append(x); selected_keys.add(x['url'])
selected=selected[:700]
OUT.write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
bycat={c:sum(1 for x in selected if x.get('cat')==c) for c in CATS}; byregion={r:sum(1 for x in selected if x.get('region')==r) for r in ('china','us','global')}
health.update({'updated':stamp,'method':'Google News public RSS discovery + existing official sources','total_collected':len(selected),'new_discovery_count':total,'direct_source_count':sum(v['count'] for k,v in health.items() if k.startswith('Direct:')),'gdelt_count':sum(v['count'] for k,v in health.items() if k.startswith('GDELT:')),'category_counts':bycat,'region_counts':byregion,'sources':health})
HEALTH.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf-8'); print('broad discovery:',total,'items; categories:',bycat,'regions:',byregion)