import json, re, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
OUT=DATA/'news.json'; HISTORY=DATA/'history.json'; COUNTRIES=DATA/'countries.json'; TIMELINE=DATA/'timeline.json'; WATCHLIST=DATA/'watchlist.json'; ALERTS=DATA/'alerts.json'
UA='China-US-Global-Intelligence-Radar/5.0'

CATS=[
('中美博弈',r'china.?us|us.?china|beijing.?washington|washington.?beijing|taiwan|semiconductor|export control|sanction|中美|台海|半导体|出口管制|制裁'),
('国防',r'military|missile|navy|air force|army|defen[cs]e|warship|exercise|drone|weapon|军事|导弹|海军|空军|陆军|国防|军舰|军演|无人机|武器'),
('外交',r'diplomacy|diplomatic|foreign ministry|ambassador|summit|alliance|nato|treaty|外交|大使|峰会|联盟|北约|条约'),
('贸易 / 供应链',r'tariff|trade|export control|import|supply chain|shipping|logistics|trade war|关税|贸易|出口管制|进口|供应链|航运|物流'),
('能源 / 资源',r'energy|oil|gas|lng|pipeline|opec|electricity|power|uranium|critical minerals|rare earth|能源|石油|天然气|液化天然气|管道|电力|铀|关键矿产|稀土'),
('科技 / AI',r'\bai\b|artificial intelligence|technology|semiconductor|chip|quantum|cloud|5g|robot|科技|人工智能|芯片|半导体|量子|机器人'),
('金融',r'bank|central bank|federal reserve|fed|interest rate|bond|currency|forex|stocks|market|finance|金融|央行|美联储|利率|债券|汇率|股市'),
('经济',r'economy|economic|gdp|inflation|employment|fiscal|monetary|growth|recession|经济|GDP|通胀|就业|财政|货币|增长|衰退'),
('产业',r'industry|manufacturing|factory|industrial|automotive|steel|产业|制造业|工厂|汽车|钢铁'),
('国家安全',r'national security|cyber|intelligence|espionage|critical infrastructure|security|国家安全|网络攻击|情报|间谍|关键基础设施|安全'),
('内政',r'domestic|protest|immigration|border|crime|healthcare|housing|education|移民|边境|抗议|治安|医保|住房|教育|内政'),
('政治',r'election|president|congress|parliament|government|political|party|cabinet|选举|总统|国会|议会|政府|政党|内阁'),
('全球政策',r'global policy|international policy|united nations|world trade|global governance|climate policy|全球政策|国际政策|联合国|全球治理|气候政策')]

COUNTRIES={'中国':(r'China|Chinese|Beijing|中国|北京','CN'),'美国':(r'United States|U\.S\.|US |American|Washington|美国','US'),'日本':(r'Japan|Japanese|日本','JP'),'韩国':(r'South Korea|Korean|韩国','KR'),'朝鲜':(r'North Korea|DPRK|朝鲜','KP'),'台湾':(r'Taiwan|台海|台湾','TW'),'俄罗斯':(r'Russia|Russian|Moscow|俄罗斯','RU'),'乌克兰':(r'Ukraine|Ukrainian|乌克兰','UA'),'印度':(r'India|Indian|印度','IN'),'巴基斯坦':(r'Pakistan|Pakistani|巴基斯坦','PK'),'越南':(r'Vietnam|Vietnamese|越南','VN'),'菲律宾':(r'Philippines|Filipino|菲律宾','PH'),'印尼':(r'Indonesia|Indonesian|印尼','ID'),'澳大利亚':(r'Australia|Australian|澳大利亚','AU'),'英国':(r'United Kingdom|Britain|British|英国','GB'),'法国':(r'France|French|法国','FR'),'德国':(r'Germany|German|德国','DE'),'波兰':(r'Poland|Polish|波兰','PL'),'土耳其':(r'Turkey|Turkish|Türkiye|土耳其','TR'),'伊朗':(r'Iran|Iranian|Tehran|伊朗','IR'),'以色列':(r'Israel|Israeli|以色列','IL'),'沙特阿拉伯':(r'Saudi Arabia|Saudi|沙特','SA'),'阿联酋':(r'United Arab Emirates|UAE|Emirati|阿联酋','AE'),'伊拉克':(r'Iraq|Iraqi|伊拉克','IQ'),'叙利亚':(r'Syria|Syrian|叙利亚','SY'),'埃及':(r'Egypt|Egyptian|埃及','EG'),'卡塔尔':(r'Qatar|Qatari|卡塔尔','QA'),'巴西':(r'Brazil|Brazilian|巴西','BR'),'墨西哥':(r'Mexico|Mexican|墨西哥','MX'),'南非':(r'South Africa|South African|南非','ZA'),'尼日利亚':(r'Nigeria|Nigerian|尼日利亚','NG')}

WATCH=[('7天','台海军事活动与高频演训信号',r'军机|军舰|军演|演训|blockade|exercise|missile','高'),('7天','中美出口管制与制裁政策变化',r'export control|sanction|semiconductor|chip|实体清单|出口管制|制裁|半导体','高'),('7–14天','能源供应与关键航运风险',r'Hormuz|Red Sea|LNG|oil|gas|shipping|霍尔木兹|红海|能源|石油|天然气','高'),('7–30天','俄乌冲突外溢与欧洲安全态势',r'Russia|Ukraine|NATO|Russia-Ukraine|俄乌|北约','中高'),('7–30天','朝鲜半岛军事与核风险信号',r'North Korea|DPRK|missile|nuclear|朝鲜|导弹|核','中高'),('7–30天','中国与美国宏观政策变化',r'Federal Reserve|Fed|interest rate|China economy|fiscal|monetary|央行|利率|财政','中'),('7–30天','全球贸易与供应链碎片化',r'tariff|trade war|export restriction|supply chain|关税|贸易战|出口限制|供应链','中')]

SOURCE_PAGES={
'White House':('https://www.whitehouse.gov/news/','official','美国','us'),
'US State Department':('https://www.state.gov/press-releases/','official','美国','us'),
'US Defense Department':('https://www.defense.gov/News/Releases/','official','美国','us'),
'US Treasury':('https://home.treasury.gov/news/press-releases','official','美国','us'),
'US Commerce':('https://www.commerce.gov/news/press-releases','official','美国','us'),
'USTR':('https://ustr.gov/about-us/policy-offices/press-office/press-releases','official','美国','us'),
'China State Council':('https://www.gov.cn/','official','中国','china'),
'China MFA':('https://www.mfa.gov.cn/eng/xw/','official','中国','china'),
'China NDRC':('https://www.ndrc.gov.cn/xwdt/','official','中国','china'),
'China PBOC':('https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html','official','中国','china'),
'China MIIT':('https://www.miit.gov.cn/xwdt/gxdt/index.html','official','中国','china'),
'China MOFCOM':('https://www.mofcom.gov.cn/article/xwfb/','official','中国','china'),
'China NBS':('https://www.stats.gov.cn/sj/zxfb/','official','中国','china')}

class LinkParser(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.href=''; self.buf=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=='a': self.href=dict(attrs).get('href',''); self.buf=[]
    def handle_data(self,data):
        if self.href:self.buf.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=='a' and self.href:
            text=re.sub(r'\s+',' ',' '.join(self.buf)).strip()
            if text:self.links.append((text,self.href))
            self.href=''; self.buf=[]

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
    with urllib.request.urlopen(req,timeout=18) as r:return r.read()
def domain_of(url):
    try:return urllib.parse.urlparse(url).netloc.lower().removeprefix('www.')
    except:return ''
def classify(t):
    for n,p in CATS:
        if re.search(p,t,re.I): return n
    return '全球政策'
def risk(t):
    if re.search(r'war|invasion|attack|missile|strike|blockade|nuclear|major sanction|战争|入侵|袭击|导弹|封锁|核|重大制裁',t,re.I):return '高'
    if re.search(r'tariff|sanction|military|security|election|energy|oil|taiwan|trade|制裁|军事|安全|选举|能源|台海|贸易',t,re.I):return '中'
    return '低'
def make_item(title,url,source,stype,region,time=''):
    return {'title':title[:220],'url':url,'source':source,'sourceType':stype,'sourceOrg':source,'sourceTier':'官方' if stype=='official' else ('权威媒体' if stype=='major_media' else '其他媒体'),'official':stype=='official','verification':'单一官方' if stype=='official' else '单一来源','time':(time or '')[:10],'region':region,'cat':classify(title),'risk':risk(title),'x':50,'y':50}

def direct_page(source,url,stype,region):
    try: raw=fetch(url)
    except Exception as e: return [],f'error:{type(e).__name__}'
    p=LinkParser(); p.feed(raw.decode('utf-8','ignore'))
    bad=re.compile(r'^(home|menu|search|subscribe|contact|about|read more|learn more|next|previous|privacy|terms|login)$',re.I)
    out=[]; seen=set()
    base=urllib.parse.urljoin(url,'/')
    for text,href in p.links:
        if len(text)<18 or bad.search(text) or text in seen: continue
        link=urllib.parse.urljoin(url,href)
        if domain_of(link)!=domain_of(url): continue
        if link.rstrip('/')==url.rstrip('/'): continue
        if not re.search(r'news|press|release|statement|brief|fact|article|2026|2025|政策|新闻|发布|公告|动态|要闻',link+' '+text,re.I): continue
        seen.add(text); out.append(make_item(text,link,source,stype,region))
        if len(out)>=25: break
    return out,'ok'

def gdelt(q,region):
    params=urllib.parse.urlencode({'query':q,'mode':'artlist','maxrecords':'50','format':'json','timespan':'24h','sort':'HybridRel'})
    url='https://api.gdeltproject.org/api/v2/doc/doc?'+params
    try: obj=json.loads(fetch(url))
    except Exception as e:return [],f'error:{type(e).__name__}'
    out=[]
    for a in obj.get('articles',[]):
        title=a.get('title','').strip(); link=a.get('url') or ''
        if title: out.append(make_item(title,link,a.get('domain','GDELT'),'major_media' if a.get('domain','').endswith(('reuters.com','apnews.com','afp.com','ft.com','bloomberg.com','wsj.com','nytimes.com','washingtonpost.com','nikkei.com','scmp.com')) else 'media',region,a.get('seendate','')))
    return out,'ok'

DATA.mkdir(exist_ok=True)
items=[]; health={}
for source,(url,stype,org,region) in SOURCE_PAGES.items():
    got,status=direct_page(source,url,stype,region); items+=got; health[source]={'method':'direct_html','status':status,'count':len(got)}

for region,q in [('china','China economy OR China military OR China security OR China policy OR China diplomacy OR China technology OR China industry OR China energy'),('us','United States economy OR US military OR US security OR US policy OR US diplomacy OR US technology OR US industry OR US energy'),('global','geopolitical risk OR global trade OR energy security OR conflict OR shipping OR global policy'),('global','China US trade OR China US technology OR China US sanctions OR Taiwan OR export control')]:
    got,status=gdelt(q,region); items+=got; health[f'GDELT-{region}-{len([k for k in health if k.startswith("GDELT-")])}']={'method':'gdelt','status':status,'count':len(got)}

try: old=json.loads(OUT.read_text(encoding='utf-8'))
except: old=[]
# Keep recent existing data if a source is temporarily unavailable.
items += old
seen=set(); uniq=[]
for x in sorted(items,key=lambda z: ({'official':0,'institution':1,'major_media':2,'media':3}.get(z.get('sourceType'),9),z.get('time','')),reverse=False):
    k=re.sub(r'[^a-z0-9]','',x.get('title','').lower())
    if k and k not in seen:seen.add(k);uniq.append(x)
uniq=uniq[:260]
now=datetime.now(timezone.utc); stamp=now.strftime('%Y-%m-%d %H:%M UTC')
for i,x in enumerate(uniq):x.update(x=8+(i*37)%84,y=8+(i*61)%84,updated=stamp)

# Correct Xinhua/People's Daily semantics if present from the supplemental collector.
for x in uniq:
    d=domain_of(x.get('url',''))
    if d in ('xinhuanet.com','people.com.cn'):
        x.update(sourceType='major_media',sourceTier='权威媒体',official=False,verification='单一来源')

OUT.write_text(json.dumps(uniq,ensure_ascii=False,indent=2),encoding='utf-8')
counts=Counter(x.get('risk') for x in uniq); region_counts={r:sum(1 for x in uniq if x.get('region')==r) for r in ('china','us','global')}
entry={'date':now.strftime('%Y-%m-%d'),'total':len(uniq),'critical':counts.get('极高',0),'high':counts.get('高',0),'medium':counts.get('中',0),'low':counts.get('低',0),**{f'{r}_items':v for r,v in region_counts.items()}}
try:history=json.loads(HISTORY.read_text(encoding='utf-8'))
except:history=[]
history=[h for h in history if h.get('date')!=entry['date']]+[entry]; HISTORY.write_text(json.dumps(history[-30:],ensure_ascii=False,indent=2),encoding='utf-8')

rows=[]
for name,(pat,code) in COUNTRIES.items():
    rel=[x for x in uniq if re.search(pat,(x.get('title','')+' '+x.get('source','')),re.I)]
    high=sum(x.get('risk')=='高' for x in rel); score=min(95,25+len(rel)*2+high*8)
    rows.append({'country':name,'code':code,'risk':round(score),'trend':'上升' if high>=2 else ('关注' if high else '稳定'),'articles':len(rel)})
COUNTRIES.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')

timeline=[]
for x in sorted(uniq,key=lambda z:z.get('time',''),reverse=True)[:80]:timeline.append({'date':x.get('time') or now.strftime('%Y-%m-%d'),'title':x.get('title'),'region':x.get('region'),'risk':x.get('risk'),'category':x.get('cat'),'source':x.get('source')})
TIMELINE.write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
watch=[]
for period,title,pat,level in WATCH:
    hits=[x for x in uniq if re.search(pat,x.get('title',''),re.I)]
    watch.append({'window':period,'title':title,'level':level,'count':len(hits),'signal':'需关注' if hits else '暂无明显新增信号','latest':hits[0]['title'] if hits else ''})
WATCHLIST.write_text(json.dumps(watch,ensure_ascii=False,indent=2),encoding='utf-8')
alerts=[]
for r in rows:
    if r['risk']>=55:alerts.append({'type':'country_risk','country':r['country'],'message':'需关注：国家风险指数处于较高区间','level':'高'})
for cat in ('中美博弈','国防','能源 / 资源'):
    n=sum(x.get('cat')==cat and x.get('risk') in ('高','中') for x in uniq)
    if n>=3:alerts.append({'type':'cluster','category':cat,'message':'信号异常：近期相关高/中风险信息较集中','level':'中高'})
ALERTS.write_text(json.dumps(alerts[:30],ensure_ascii=False,indent=2),encoding='utf-8')

# Machine-readable health file used by the workflow/UI.
(DATA/'collection_health.json').write_text(json.dumps({'updated':stamp,'total_collected':len(uniq),'direct_source_count':sum(v['count'] for v in health.values() if v.get('method')=='direct_html'),'gdelt_count':sum(v['count'] for v in health.values() if v.get('method')=='gdelt'),'sources':health},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'total':len(uniq),'direct':sum(v['count'] for v in health.values() if v.get('method')=='direct_html'),'gdelt':sum(v['count'] for v in health.values() if v.get('method')=='gdelt'),'health':health},ensure_ascii=False))
