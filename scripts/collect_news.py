import json, re, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; OUT=DATA/'news.json'; HISTORY=DATA/'history.json'; COUNTRIES=DATA/'countries.json'; TIMELINE=DATA/'timeline.json'; WATCHLIST=DATA/'watchlist.json'; ALERTS=DATA/'alerts.json'
UA='China-US-Global-Intelligence-Radar/4.0'

QUERIES={
 'china':'China economy OR China military OR China security OR China policy OR China diplomacy OR China technology OR China industry OR China energy',
 'us':'United States economy OR US military OR US security OR US policy OR US diplomacy OR US technology OR US industry OR US energy',
 'global':'geopolitical risk OR global trade OR energy security OR conflict OR shipping OR global policy',
 'competition':'China US trade OR China US technology OR China US sanctions OR Taiwan OR export control'
}
OFFICIAL_DOMAINS=set('gov.cn mfa.gov.cn fmprc.gov.cn mod.gov.cn pbc.gov.cn stats.gov.cn ndrc.gov.cn miit.gov.cn mofcom.gov.cn customs.gov.cn nea.gov.cn cac.gov.cn most.gov.cn mof.gov.cn whitehouse.gov state.gov defense.gov treasury.gov federalreserve.gov commerce.gov ustr.gov energy.gov eia.gov bls.gov bea.gov nist.gov congress.gov un.org wto.org imf.org worldbank.org iea.org oecd.org bis.org iaea.org'.split())
INSTITUTION_DOMAINS=set('imf.org worldbank.org wto.org iea.org oecd.org bis.org un.org iaea.org'.split())
MAJOR_MEDIA_DOMAINS=set('reuters.com apnews.com afp.com ft.com bloomberg.com wsj.com nytimes.com washingtonpost.com economist.com nikkei.com scmp.com'.split())

CATS=[
 ('政治',r'election|president|congress|parliament|government|political|party|cabinet|选举|总统|国会|议会|政府|政党|内阁'),
 ('金融',r'bank|central bank|federal reserve|fed|interest rate|bond|currency|forex|stocks|market|金融|央行|美联储|利率|债券|汇率|股市'),
 ('经济',r'economy|economic|gdp|inflation|employment|fiscal|monetary|economic growth|recession|经济|GDP|通胀|就业|财政|货币|增长|衰退'),
 ('产业',r'industry|manufacturing|factory|industrial|semiconductor industry|automotive|steel|产业|制造业|工厂|汽车|钢铁'),
 ('科技 / AI',r'ai|artificial intelligence|technology|semiconductor|chip|quantum|cloud|5g|robot|科技|人工智能|芯片|半导体|量子|机器人'),
 ('国防',r'military|missile|navy|air force|army|defen[cs]e|warship|exercise|drone|weapon|armed forces|军事|导弹|海军|空军|陆军|国防|军舰|军演|无人机|武器'),
 ('内政',r'domestic|protest|immigration|border|crime|healthcare|social security|housing|education|移民|边境|抗议|治安|医保|住房|教育|内政'),
 ('国家安全',r'security|terror|cyber|intelligence|counterintelligence|espionage|critical infrastructure|national security|安全|网络攻击|情报|间谍|关键基础设施|国家安全'),
 ('外交',r'diplomacy|diplomatic|foreign ministry|ambassador|summit|alliance|nato|treaty|外交|大使|峰会|联盟|北约|条约'),
 ('贸易 / 供应链',r'tariff|trade|export control|import|supply chain|shipping|logistics|trade war|关税|贸易|出口管制|进口|供应链|航运|物流'),
 ('能源 / 资源',r'energy|oil|gas|lng|pipeline|opec|electricity|power|uranium|critical minerals|rare earth|能源|石油|天然气|液化天然气|管道|电力|铀|关键矿产|稀土'),
 ('中美博弈',r'china.?us|us.?china|beijing.?washington|washington.?beijing|taiwan|semiconductor|chip|export control|sanction|中美|台海|半导体|芯片|出口管制|制裁'),
 ('全球政策',r'global policy|international policy|united nations|world trade|global governance|climate policy|sanctions regime|全球政策|国际政策|联合国|全球治理|气候政策|制裁机制')
]
COUNTRY_NAMES={'中国':r'China|Chinese|Beijing|中国|北京','美国':r'United States|U\.S\.|US |American|Washington|美国','日本':r'Japan|Japanese|日本','韩国':r'South Korea|Korean|韩国','朝鲜':r'North Korea|DPRK|朝鲜','台湾':r'Taiwan|台海|台湾','俄罗斯':r'Russia|Russian|Moscow|俄罗斯','乌克兰':r'Ukraine|Ukrainian|乌克兰','印度':r'India|Indian|印度','巴基斯坦':r'Pakistan|Pakistani|巴基斯坦','越南':r'Vietnam|Vietnamese|越南','菲律宾':r'Philippines|Filipino|菲律宾','印尼':r'Indonesia|Indonesian|印尼','澳大利亚':r'Australia|Australian|澳大利亚','英国':r'United Kingdom|Britain|British|英国','法国':r'France|French|法国','德国':r'Germany|German|德国','波兰':r'Poland|Polish|波兰','土耳其':r'Turkey|Turkish|Türkiye|土耳其','伊朗':r'Iran|Iranian|Tehran|伊朗','以色列':r'Israel|Israeli|以色列','沙特阿拉伯':r'Saudi Arabia|Saudi|沙特','阿联酋':r'United Arab Emirates|UAE|Emirati|阿联酋','伊拉克':r'Iraq|Iraqi|伊拉克','叙利亚':r'Syria|Syrian|叙利亚','埃及':r'Egypt|Egyptian|埃及','卡塔尔':r'Qatar|Qatari|卡塔尔','巴西':r'Brazil|Brazilian|巴西','墨西哥':r'Mexico|Mexican|墨西哥','南非':r'South Africa|South African|南非','尼日利亚':r'Nigeria|Nigerian|尼日利亚'}
CODE_MAP={'中国':'CN','美国':'US','日本':'JP','韩国':'KR','朝鲜':'KP','台湾':'TW','俄罗斯':'RU','乌克兰':'UA','印度':'IN','巴基斯坦':'PK','越南':'VN','菲律宾':'PH','印尼':'ID','澳大利亚':'AU','英国':'GB','法国':'FR','德国':'DE','波兰':'PL','土耳其':'TR','伊朗':'IR','以色列':'IL','沙特阿拉伯':'SA','阿联酋':'AE','伊拉克':'IQ','叙利亚':'SY','埃及':'EG','卡塔尔':'QA','巴西':'BR','墨西哥':'MX','南非':'ZA','尼日利亚':'NG'}
WATCH=[('7天','台海军事活动与高频演训信号',r'军机|军舰|军演|演训|blockade|exercise|missile','高'),('7天','中美出口管制与制裁政策变化',r'export control|sanction|semiconductor|chip|实体清单|出口管制|制裁|半导体','高'),('7–14天','能源供应与关键航运风险',r'Hormuz|Red Sea|LNG|oil|gas|shipping|霍尔木兹|红海|能源|石油|天然气','高'),('7–30天','俄乌冲突外溢与欧洲安全态势',r'Russia|Ukraine|NATO|Russia-Ukraine|俄乌|北约','中高'),('7–30天','朝鲜半岛军事与核风险信号',r'North Korea|DPRK|missile|nuclear|朝鲜|导弹|核','中高'),('7–30天','中国与美国宏观政策变化',r'Federal Reserve|Fed|interest rate|China economy|fiscal|monetary|央行|利率|财政','中'),('7–30天','全球贸易与供应链碎片化',r'tariff|trade war|export restriction|supply chain|关税|贸易战|出口限制|供应链','中')]

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=20) as r:return r.read()
def clean(s):return re.sub(r'<[^>]+>|\s+',' ',s or '').strip()
def domain_of(url):
    try:return urllib.parse.urlparse(url).netloc.lower().split(':')[0].removeprefix('www.')
    except Exception:return ''
def source_meta(url):
    d=domain_of(url)
    if d in OFFICIAL_DOMAINS or d.endswith('.gov.cn') or d.endswith('.gov') or d.endswith('.mil'):
        org=d; return 'official',org,'官方'
    if d in INSTITUTION_DOMAINS:return 'institution',d,'国际机构'
    if d in MAJOR_MEDIA_DOMAINS:return 'major_media',d,'权威媒体'
    return 'media',d or 'GDELT','其他媒体'
def category(t):
    # Prioritize strategic cross-domain categories before generic economic/security matches.
    for name,p in CATS:
        if re.search(p,t,re.I):return name
    return '全球政策'
def risk(t):
    if re.search(r'war|invasion|attack|missile|strike|blockade|nuclear|major sanction|重大冲突|战争|入侵|袭击|导弹|封锁|核',t,re.I):return '高'
    if re.search(r'tariff|sanction|military|security|election|energy|oil|taiwan|trade|制裁|军事|安全|选举|能源|台海|贸易',t,re.I):return '中'
    return '低'
def gdelt(q,region):
    params=urllib.parse.urlencode({'query':q,'mode':'artlist','maxrecords':'40','format':'json','timespan':'24h','sort':'HybridRel'})
    try:
        obj=json.loads(fetch('https://api.gdeltproject.org/api/v2/doc/doc?'+params)); out=[]
        for a in obj.get('articles',[]):
            title=clean(a.get('title')); url=a.get('url') or ''
            if title:
                st,org,tier=source_meta(url)
                out.append({'title':title,'url':url,'source':a.get('domain','GDELT'),'sourceType':st,'sourceOrg':org,'sourceTier':tier,'official':st=='official','verification':'单一来源','time':a.get('seendate','')[:10],'region':region,'cat':category(title),'risk':risk(title)})
        return out
    except Exception:return []

items=[]
for region,q in QUERIES.items(): items += gdelt(q,'global' if region=='competition' else region)
# Official-first discovery layer: ask GDELT specifically for high-value government/institutional domains.
official_queries=[
 ('china','domainis:gov.cn OR domainis:mfa.gov.cn OR domainis:mod.gov.cn OR domainis:pbc.gov.cn OR domainis:ndrc.gov.cn OR domainis:miit.gov.cn OR domainis:mofcom.gov.cn OR domainis:nea.gov.cn'),
 ('us','domainis:whitehouse.gov OR domainis:state.gov OR domainis:defense.gov OR domainis:treasury.gov OR domainis:federalreserve.gov OR domainis:commerce.gov OR domainis:ustr.gov OR domainis:energy.gov'),
 ('global','domainis:un.org OR domainis:wto.org OR domainis:imf.org OR domainis:worldbank.org OR domainis:iea.org OR domainis:oecd.org OR domainis:bis.org OR domainis:iaea.org')
]
for region,q in official_queries: items += gdelt(q,'global' if region=='global' else region)
seen=set(); uniq=[]
# Prefer official/institutional copies when the same title appears more than once.
for x in sorted(items,key=lambda z:({'official':0,'institution':1,'major_media':2,'media':3}.get(z['sourceType'],9), z.get('time','')),):
    key=re.sub(r'[^a-z0-9]','',x['title'].lower())
    if key and key not in seen: seen.add(key); uniq.append(x)
uniq=uniq[:220]
now=datetime.now(timezone.utc); stamp=now.strftime('%Y-%m-%d %H:%M UTC')
for i,x in enumerate(uniq): x.update(x=8+(i*37)%84,y=8+(i*61)%84,updated=stamp)
# Mark identical-title corroboration across source tiers.
title_groups={}
for x in uniq:title_groups.setdefault(re.sub(r'[^a-z0-9]','',x['title'].lower()),[]).append(x)
for group in title_groups.values():
    tiers={x['sourceType'] for x in group}
    if len(tiers)>=3:v='多源交叉'
    elif len(tiers)>=2:v='双源交叉'
    else:v='单一官方' if group[0]['sourceType']=='official' else '单一来源'
    for x in group:x['verification']=v
DATA.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(uniq,ensure_ascii=False,indent=2),encoding='utf-8')
counts=Counter(x['risk'] for x in uniq); region_counts={r:sum(1 for x in uniq if x['region']==r) for r in ('china','us','global')}
entry={'date':now.strftime('%Y-%m-%d'),'total':len(uniq),'critical':counts.get('极高',0),'high':counts.get('高',0),'medium':counts.get('中',0),'low':counts.get('低',0),**{f'{r}_items':v for r,v in region_counts.items()}}
try: history=json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else []
except Exception: history=[]
previous_history=history[-1] if history else None
history=[h for h in history if h.get('date')!=entry['date']]+[entry]; history=history[-30:]; HISTORY.write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')

try: old=json.loads(COUNTRIES.read_text(encoding='utf-8')) if COUNTRIES.exists() else []
except Exception: old=[]
oldmap={x.get('code'):x for x in old}; country_rows=[]
for name,pat in COUNTRY_NAMES.items():
    related=[x for x in uniq if re.search(pat,x['title'],re.I)]
    weighted=sum({'极高':100,'高':70,'中':40,'低':15}.get(x['risk'],0) for x in related)
    s=round(weighted/len(related)) if related else 0
    s=min(100,round(s*(0.55+0.45*min(len(related),10)/10))) if related else 0
    prev=oldmap.get(CODE_MAP[name],{}).get('score',0); trend=1 if s>prev+5 else -1 if s<prev-5 else 0
    top=Counter(x['cat'] for x in related).most_common(1); latest=related[0]['title'] if related else '暂无新情报'
    country_rows.append({'name':name,'code':CODE_MAP[name],'score':s,'trend':trend,'delta':s-prev,'driver':top[0][0] if top else '暂无数据','latest':latest,'articles':len(related),'updated':stamp})
COUNTRIES.write_text(json.dumps(country_rows,ensure_ascii=False,indent=2),encoding='utf-8')

top_events=sorted(uniq,key=lambda x:{'极高':4,'高':3,'中':2,'低':1}.get(x['risk'],0),reverse=True)[:40]
TIMELINE.write_text(json.dumps({'updated':stamp,'events':[{'date':x['time'] or entry['date'],'title':x['title'],'risk':x['risk'],'category':x['cat'],'region':x['region'],'url':x.get('url'),'source':x.get('source'),'sourceTier':x.get('sourceTier'),'verification':x.get('verification')} for x in top_events]},ensure_ascii=False,indent=2),encoding='utf-8')

watch=[]
for window,title,pat,priority in WATCH:
    hits=[x for x in uniq if re.search(pat,x['title'],re.I)]
    watch.append({'window':window,'title':title,'trigger':f'当前24小时相关信号 {len(hits)} 条；若未来继续增加则提高关注级别','priority':priority,'signals':len(hits),'note':'观察事项，不代表事件必然发生。'})
WATCHLIST.write_text(json.dumps({'updated':stamp,'items':watch},ensure_ascii=False,indent=2),encoding='utf-8')

alerts=[]
for c in country_rows:
    if c['delta']>=15: alerts.append({'severity':'高','type':'国家风险跃升','title':f"{c['name']} 风险指数单日上升 {c['delta']} 点",'reason':f"当前 {c['score']}/100；主要驱动：{c['driver']}；相关报道 {c['articles']} 条。",'country':c['name'],'time':stamp,'evidence':c['latest']})
prev_total=(previous_history or {}).get('total',0) if previous_history else 0
prev_high=((previous_history or {}).get('high',0)+(previous_history or {}).get('critical',0)) if previous_history else 0
cur_high=counts.get('高',0)+counts.get('极高',0)
if prev_total>=10 and len(uniq)>=prev_total*1.8: alerts.append({'severity':'中','type':'情报量异常','title':'今日公开情报量较前一日明显放大','reason':f'今日 {len(uniq)} 条，前一日 {prev_total} 条，超过 1.8 倍阈值。','time':stamp,'evidence':'news.json'})
if prev_high>=5 and cur_high>=prev_high*2: alerts.append({'severity':'高','type':'高风险信号放大','title':'高风险情报量较前一日翻倍','reason':f'今日高/极高 {cur_high} 条，前一日 {prev_high} 条。','time':stamp,'evidence':'news.json'})
cat_counts=Counter(x['cat'] for x in uniq)
if cat_counts['中美博弈']>=5 and cat_counts['国防']>=5 and cat_counts['能源 / 资源']>=5: alerts.append({'severity':'高','type':'多领域联动','title':'中美博弈、国防与能源/资源信号同时偏强','reason':f"中美博弈 {cat_counts['中美博弈']} 条；国防 {cat_counts['国防']} 条；能源/资源 {cat_counts['能源 / 资源']} 条。",'time':stamp,'evidence':'今日分类统计'})
ALERTS.write_text(json.dumps({'updated':stamp,'alerts':alerts[:12]},ensure_ascii=False,indent=2),encoding='utf-8')
print(f'wrote {len(uniq)} news, {len(country_rows)} countries, {len(top_events)} timeline events, {len(alerts)} alerts')
