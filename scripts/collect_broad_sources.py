import json,re,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'news.json'; HEALTH=DATA/'collection_health.json'
UA='China-US-Global-Intelligence-Radar/BroadCollector-5.0'
CATS={'政治':'president election congress parliament government politics cabinet political 选举 总统 国会 政府 政治 内阁','金融':'central bank interest rate bond currency stocks banking finance monetary 美联储 央行 利率 债券 汇率 股市 金融','经济':'economy economic GDP inflation employment growth recession fiscal 经济 GDP 通胀 就业 增长 衰退 财政','产业':'industry manufacturing factory automotive steel industrial 产业 制造业 工厂 汽车 钢铁','科技 / AI':'AI artificial intelligence semiconductor chip technology quantum cloud robotics 科技 人工智能 半导体 芯片 量子 机器人','国防':'military defense missile navy air force army warship exercise drone weapon 国防 军事 导弹 海军 空军 军演 武器','内政':'domestic immigration border crime healthcare housing education protest 内政 移民 边境 治安 医疗 住房 教育 抗议','国家安全':'national security cyber intelligence espionage critical infrastructure security 国家安全 网络 情报 间谍 关键基础设施 安全','外交':'diplomacy diplomatic foreign ministry ambassador summit alliance NATO treaty 外交 大使 峰会 联盟 北约 条约','贸易 / 供应链':'trade tariff export import supply chain shipping logistics trade war 贸易 关税 出口 进口 供应链 航运 物流','能源 / 资源':'energy oil gas LNG pipeline OPEC electricity power uranium rare earth critical minerals 能源 石油 天然气 液化天然气 管道 电力 铀 稀土','中美博弈':'China US US China Taiwan export control sanctions semiconductor trade 中美 台海 出口管制 制裁 半导体','全球政策':'global policy international policy United Nations WTO global governance climate policy sanctions 全球政策 国际政策 联合国 全球治理 气候政策 制裁'}
MEDIA={'reuters.com','apnews.com','ft.com','bloomberg.com','wsj.com','nytimes.com','washingtonpost.com','scmp.com','nikkei.com','afp.com','bbc.com','bbc.co.uk','aljazeera.com','dw.com','npr.org'}
OFFICIAL_PAGES=[
('White House','https://www.whitehouse.gov/news/','us'),('US State Department','https://www.state.gov/press-releases/','us'),('US Defense Department','https://www.defense.gov/News/Releases/','us'),('US Treasury','https://home.treasury.gov/news/press-releases','us'),('US Commerce','https://www.commerce.gov/news/press-releases','us'),('USTR','https://ustr.gov/about-us/policy-offices/press-office/press-releases','us'),('Federal Reserve','https://www.federalreserve.gov/newsevents/pressreleases.htm','us'),('EIA','https://www.eia.gov/todayinenergy/','us'),('BLS','https://www.bls.gov/news.release/','us'),('BEA','https://www.bea.gov/news','us'),('China State Council','https://www.gov.cn/english/','china'),('China MFA','https://www.mfa.gov.cn/eng/xw/','china'),('China NDRC','https://www.ndrc.gov.cn/xwdt/','china'),('China PBOC','https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html','china'),('China MIIT','https://www.miit.gov.cn/xwdt/gxdt/index.html','china'),('China MOFCOM','https://www.mofcom.gov.cn/article/xwfb/','china'),('China NBS','https://www.stats.gov.cn/sj/zxfb/','china'),('China MOD','https://eng.mod.gov.cn/','china'),('UN News','https://news.un.org/en/','global'),('WTO News','https://www.wto.org/english/news_e/news_e.htm','global'),('IMF News','https://www.imf.org/en/News','global'),('World Bank News','https://www.worldbank.org/en/news','global'),('IAEA News','https://www.iaea.org/newscenter/news','global'),('OECD News','https://www.oecd.org/en/about/news.html','global')]
OFFICIAL_FEEDS=[('Federal Reserve','https://www.federalreserve.gov/feeds/press_all.xml','us','金融'),('Federal Reserve speeches','https://www.federalreserve.gov/feeds/speeches.xml','us','金融'),('BLS','https://www.bls.gov/feed/bls_latest.rss','us','经济'),('EIA','https://www.eia.gov/rss/todayinenergy.xml','us','能源 / 资源'),('IAEA','https://www.iaea.org/feeds/topnews','global','全球政策')]
MEDIA_FEEDS=[('BBC Asia','https://feeds.bbci.co.uk/news/world/asia/rss.xml','china'),('BBC US','https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml','us'),('BBC World','https://feeds.bbci.co.uk/news/world/rss.xml','global'),('DW World','https://rss.dw.com/rdf/rss-en-all','global'),('Al Jazeera','https://www.aljazeera.com/xml/rss/all.xml','global'),('NPR World','https://feeds.npr.org/1004/rss.xml','global')]
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml,application/xml,text/xml,text/html,*/*'})
 with urllib.request.urlopen(req,timeout=20) as r:return r.read()
def domain(url):return urllib.parse.urlparse(url).netloc.lower().removeprefix('www.')
def risk(t):
 if re.search(r'war|attack|strike|missile|blockade|nuclear|invasion|战争|袭击|导弹|封锁|核|入侵',t,re.I):return '高'
 if re.search(r'sanction|tariff|military|security|energy|oil|trade|election|制裁|关税|军事|安全|能源|石油|贸易|选举',t,re.I):return '中'
 return '低'
def cat(t,hint=''):
 for c,terms in CATS.items():
  if hint==c:return c
 for c,terms in CATS.items():
  if re.search(terms,t,re.I):return c
 return '全球政策'
def item(title,url,source,stype,region,cat_hint='',time=''):
 tier='官方' if stype=='official' else ('权威媒体' if stype=='major_media' else '其他媒体')
 return {'title':re.sub(r'\s+',' ',title).strip()[:240],'url':url,'source':source,'sourceType':stype,'sourceOrg':source,'sourceTier':tier,'official':stype=='official','verification':'单一官方' if stype=='official' else '单一来源','time':str(time)[:80],'region':region,'cat':cat(title,cat_hint),'risk':risk(title),'x':50,'y':50}
def parse_rss(raw,source,region,cat_hint=''):
 try:root=ET.fromstring(raw)
 except Exception:return []
 out=[]
 for n in root.findall('.//item')[:60]:
  title=(n.findtext('title') or '').strip(); link=(n.findtext('link') or '').strip(); pub=(n.findtext('pubDate') or n.findtext('{http://purl.org/dc/elements/1.1/}date') or '').strip()
  if title and link:out.append(item(title,link,source,'official' if source in {x[0] for x in OFFICIAL_FEEDS} else 'media',region,cat_hint,pub))
 return out
def official_page(source,url,region):
 try:raw=fetch(url).decode('utf-8','ignore')
 except Exception as e:return [],f'error:{type(e).__name__}'
 links=re.findall(r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>',raw,re.I|re.S); out=[];seen=set()
 for href,text in links:
  text=re.sub('<[^>]+>',' ',text);text=re.sub(r'\s+',' ',text).strip();link=urllib.parse.urljoin(url,href)
  if len(text)<20 or link in seen or domain(link)!=domain(url):continue
  if not re.search(r'news|press|release|statement|brief|fact|article|2026|2025|政策|新闻|发布|公告|动态|要闻',link+' '+text,re.I):continue
  seen.add(link);out.append(item(text,link,source,'official',region,'', ''))
  if len(out)>=50:break
 return out,'ok'
def search_rss(query,region,lang='en-US',country='US'):
 urls=[('GoogleNews','https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':lang,'gl':country,'ceid':country+':en'})),('BingNews','https://www.bing.com/news/search?'+urllib.parse.urlencode({'q':query,'format':'rss'}))]
 for source,url in urls:
  try:
   got=parse_rss(fetch(url),source,region)
   if got:return got,'ok:'+source
  except Exception as e:status=f'error:{type(e).__name__}'
 return [],status if 'status' in locals() else 'error'
items=[];health={};new_discovery=0;official_direct=0
for source,url,region in OFFICIAL_PAGES:
 got,status=official_page(source,url,region);items+=got;official_direct+=len(got);health['OfficialPage:'+source]={'method':'direct_first_party_html','status':status,'count':len(got)}
for source,url,region,c in OFFICIAL_FEEDS:
 try:got=parse_rss(fetch(url),source,region,c);status='ok'
 except Exception as e:got=[];status=f'error:{type(e).__name__}'
 items+=got;official_direct+=len(got);health['OfficialFeed:'+source]={'method':'direct_first_party_rss','status':status,'count':len(got)}
queries=[('china','China policy economy military security diplomacy technology trade energy','en-US','US'),('us','United States policy economy military security diplomacy technology trade energy','en-US','US'),('global','global policy geopolitics trade energy security conflict diplomacy','en-US','US'),('global','China US relations tariffs sanctions semiconductors Taiwan export controls','en-US','US'),('china','中国 政策 经济 军事 外交 科技 贸易 能源','zh-CN','CN')]
for region,q,lang,country in queries:
 got,status=search_rss(q,region,lang,country);items+=got;new_discovery+=len(got);health['Search:'+region+':'+lang]={'method':'GoogleNews/Bing RSS fallback','status':status,'count':len(got)}
for source,url,region in MEDIA_FEEDS:
 try:got=parse_rss(fetch(url),source,region);status='ok'
 except Exception as e:got=[];status=f'error:{type(e).__name__}'
 items+=got;health['MediaFeed:'+source]={'method':'public_media_rss','status':status,'count':len(got)}
try:old=json.loads(OUT.read_text(encoding='utf-8'))
except Exception:old=[]
items+=old;seen=set();uniq=[]
for x in items:
 k=re.sub(r'[^a-z0-9]','',x.get('url','').lower()) or re.sub(r'[^a-z0-9]','',x.get('title','').lower())
 if k and k not in seen:seen.add(k);uniq.append(x)
uniq=[x for x in uniq if len(x.get('title',''))>=18]
uniq.sort(key=lambda x:x.get('time') or x.get('updated') or '',reverse=True)
selected=uniq[:12000];stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
for i,x in enumerate(selected):x['updated']=stamp;x['x']=8+(i*37)%84;x['y']=8+(i*61)%84
bycat={c:sum(1 for x in selected if x.get('cat')==c) for c in CATS};byregion={r:sum(1 for x in selected if x.get('region')==r) for r in ('china','us','global')};official_count=sum(1 for x in selected if x.get('official'))
health.update({'updated':stamp,'method':'direct first-party HTML/RSS + Google/Bing RSS fallback + public media RSS + retained archive feed','total_collected':len(selected),'new_discovery_count':new_discovery,'official_direct_count':official_direct,'official_in_working_set':official_count,'category_counts':bycat,'region_counts':byregion,'sources':health})
OUT.write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8');HEALTH.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf-8');print('broad discovery:',new_discovery,'official direct:',official_direct,'working set:',len(selected),'official retained:',official_count,'categories:',bycat,'regions:',byregion)