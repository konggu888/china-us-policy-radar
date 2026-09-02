import json, re, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; OUT=DATA/'news.json'; HISTORY=DATA/'history.json'; COUNTRIES=DATA/'countries.json'; TIMELINE=DATA/'timeline.json'; WATCHLIST=DATA/'watchlist.json'
UA='China-US-Global-Intelligence-Radar/2.0'
QUERIES={'china':'China economy OR China military OR China security OR China policy','us':'United States economy OR US military OR US security OR US policy','global':'geopolitical risk OR global trade OR energy security OR conflict OR shipping','competition':'China US trade OR China US technology OR China US sanctions OR Taiwan'}
CATS=[('能源安全',r'energy|oil|gas|lng|pipeline|opec|electricity|power|uranium|能源|石油|天然气|液化气|电力'),('军事',r'military|missile|navy|air force|army|defen[cs]e|warship|exercise|drone|weapon|军事|导弹|军舰|军演'),('安全',r'security|terror|cyber|border|intelligence|sanction|安全|网络攻击|制裁|边境'),('金融经济',r'economy|economic|market|stocks|inflation|interest rate|tariff|trade|gdp|bank|debt|金融|经济|关税|贸易|通胀'),('内政',r'election|congress|government|president|parliament|protest|domestic|policy|选举|国会|政府|总统|内政'),('中美竞争',r'china.?us|us.?china|beijing|washington|taiwan|semiconductor|chip|technology|中美|台海|芯片|半导体'),('全球化',r'globalization|global trade|supply chain|deglobal|全球化|供应链')]
COUNTRY_NAMES={'中国':r'China|Chinese|Beijing|中国|北京','美国':r'United States|U\.S\.|US |American|Washington|美国','日本':r'Japan|Japanese|日本','韩国':r'South Korea|Korean|韩国','朝鲜':r'North Korea|DPRK|朝鲜','台湾':r'Taiwan|台海|台湾','俄罗斯':r'Russia|Russian|Moscow|俄罗斯','乌克兰':r'Ukraine|Ukrainian|乌克兰','印度':r'India|Indian|印度','巴基斯坦':r'Pakistan|Pakistani|巴基斯坦','越南':r'Vietnam|Vietnamese|越南','菲律宾':r'Philippines|Filipino|菲律宾','印尼':r'Indonesia|Indonesian|印尼','澳大利亚':r'Australia|Australian|澳大利亚','英国':r'United Kingdom|Britain|British|英国','法国':r'France|French|法国','德国':r'Germany|German|德国','波兰':r'Poland|Polish|波兰','土耳其':r'Turkey|Turkish|Türkiye|土耳其','伊朗':r'Iran|Iranian|Tehran|伊朗','以色列':r'Israel|Israeli|以色列','沙特阿拉伯':r'Saudi Arabia|Saudi|沙特','阿联酋':r'United Arab Emirates|UAE|Emirati|阿联酋','伊拉克':r'Iraq|Iraqi|伊拉克','叙利亚':r'Syria|Syrian|叙利亚','埃及':r'Egypt|Egyptian|埃及','卡塔尔':r'Qatar|Qatari|卡塔尔','巴西':r'Brazil|Brazilian|巴西','墨西哥':r'Mexico|Mexican|墨西哥','南非':r'South Africa|South African|南非','尼日利亚':r'Nigeria|Nigerian|尼日利亚'}
WATCH=[('7天','台海军事活动与高频演训信号',r'军机|军舰|军演|演训|blockade|exercise|missile','高'),('7天','中美出口管制与制裁政策变化',r'export control|sanction|semiconductor|chip|实体清单|出口管制|制裁|半导体','高'),('7–14天','能源供应与关键航运风险',r'Hormuz|Red Sea|LNG|oil|gas|shipping|霍尔木兹|红海|能源|石油|天然气','高'),('7–30天','俄乌冲突外溢与欧洲安全态势',r'Russia|Ukraine|NATO|Russia-Ukraine|俄乌|北约','中高'),('7–30天','朝鲜半岛军事与核风险信号',r'North Korea|DPRK|missile|nuclear|朝鲜|导弹|核','中高'),('7–30天','中国与美国宏观政策变化',r'Federal Reserve|Fed|interest rate|China economy|fiscal|monetary|央行|利率|财政','中'),('7–30天','全球贸易与供应链碎片化',r'tariff|trade war|export restriction|supply chain|关税|贸易战|出口限制|供应链','中')]

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=20) as r:return r.read()
def clean(s):return re.sub(r'<[^>]+>|\s+',' ',s or '').strip()
def category(t):
    for name,p in CATS:
        if re.search(p,t,re.I):return name
    return '全球化'
def risk(t):
    if re.search(r'war|invasion|attack|missile|strike|blockade|nuclear|major sanction|重大冲突|战争|入侵|袭击|导弹|封锁|核',t,re.I):return '高'
    if re.search(r'tariff|sanction|military|security|election|energy|oil|taiwan|trade|制裁|军事|安全|选举|能源|台海|贸易',t,re.I):return '中'
    return '低'
def gdelt(q,region):
    params=urllib.parse.urlencode({'query':q,'mode':'artlist','maxrecords':'40','format':'json','timespan':'24h','sort':'HybridRel'})
    try:
        obj=json.loads(fetch('https://api.gdeltproject.org/api/v2/doc/doc?'+params)); out=[]
        for a in obj.get('articles',[]):
            title=clean(a.get('title'))
            if title: out.append({'title':title,'url':a.get('url'),'source':a.get('domain','GDELT'),'time':a.get('seendate','')[:10],'region':region,'cat':category(title),'risk':risk(title)})
        return out
    except Exception:return []
items=[]
for region,q in QUERIES.items(): items += gdelt(q,'global' if region=='competition' else region)
seen=set(); uniq=[]
for x in items:
    key=re.sub(r'[^a-z0-9]','',x['title'].lower())
    if key and key not in seen: seen.add(key); uniq.append(x)
uniq=uniq[:180]
now=datetime.now(timezone.utc); stamp=now.strftime('%Y-%m-%d %H:%M UTC')
for i,x in enumerate(uniq): x.update(x=8+(i*37)%84,y=8+(i*61)%84,updated=stamp)
DATA.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(uniq,ensure_ascii=False,indent=2),encoding='utf-8')
counts=Counter(x['risk'] for x in uniq); region_counts={r:sum(1 for x in uniq if x['region']==r) for r in ('china','us','global')}
entry={'date':now.strftime('%Y-%m-%d'),'total':len(uniq),'critical':counts.get('极高',0),'high':counts.get('高',0),'medium':counts.get('中',0),'low':counts.get('低',0),**{f'{r}_items':v for r,v in region_counts.items()}}
try: history=json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else []
except Exception: history=[]
history=[h for h in history if h.get('date')!=entry['date']]+[entry]; history=history[-30:]; HISTORY.write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')

# Country risk matrix: article count + risk weight, compared with previous day when available.
try: old=json.loads(COUNTRIES.read_text(encoding='utf-8')) if COUNTRIES.exists() else []
except Exception: old=[]
oldmap={x.get('code'):x for x in old}
country_rows=[]
for name,pat in COUNTRY_NAMES.items():
    related=[x for x in uniq if re.search(pat,x['title'],re.I)]
    weighted=sum({'极高':100,'高':70,'中':40,'低':15}.get(x['risk'],0) for x in related)
    s=round(weighted/len(related)) if related else 0
    # volume-adjusted signal: more relevant reporting increases attention, capped at 100.
    s=min(100,round(s*(0.55+0.45*min(len(related),10)/10))) if related else 0
    prev=oldmap.get(next((c.get('code') for c in old if c.get('name')==name),''),{}).get('score',0)
    trend=1 if s>prev+5 else -1 if s<prev-5 else 0
    top=Counter(x['cat'] for x in related).most_common(1); latest=related[0]['title'] if related else '暂无新情报'
    code=next((c for c in ['CN','US','JP','KR','KP','TW','RU','UA','IN','PK','VN','PH','ID','AU','GB','FR','DE','PL','TR','IR','IL','SA','AE','IQ','SY','EG','QA','BR','MX','ZA','NG'] if any(v==c for n,v in [])), '')
    code_map={'中国':'CN','美国':'US','日本':'JP','韩国':'KR','朝鲜':'KP','台湾':'TW','俄罗斯':'RU','乌克兰':'UA','印度':'IN','巴基斯坦':'PK','越南':'VN','菲律宾':'PH','印尼':'ID','澳大利亚':'AU','英国':'GB','法国':'FR','德国':'DE','波兰':'PL','土耳其':'TR','伊朗':'IR','以色列':'IL','沙特阿拉伯':'SA','阿联酋':'AE','伊拉克':'IQ','叙利亚':'SY','埃及':'EG','卡塔尔':'QA','巴西':'BR','墨西哥':'MX','南非':'ZA','尼日利亚':'NG'}[name]
    country_rows.append({'name':name,'code':code_map,'score':s,'trend':trend,'driver':top[0][0] if top else '暂无数据','latest':latest,'articles':len(related),'updated':stamp})
COUNTRIES.write_text(json.dumps(country_rows,ensure_ascii=False,indent=2),encoding='utf-8')

# Timeline: top risk events, compact enough for a static dashboard.
top_events=sorted(uniq,key=lambda x:{'极高':4,'高':3,'中':2,'低':1}.get(x['risk'],0),reverse=True)[:40]
TIMELINE.write_text(json.dumps({'updated':stamp,'events':[{'date':x['time'] or entry['date'],'title':x['title'],'risk':x['risk'],'category':x['cat'],'region':x['region'],'url':x.get('url'),'source':x.get('source')} for x in top_events]},ensure_ascii=False,indent=2),encoding='utf-8')

# Watchlist is evidence-trigger based, not a prediction engine.
watch=[]
for window,title,pat,priority in WATCH:
    hits=[x for x in uniq if re.search(pat,x['title'],re.I)]
    watch.append({'window':window,'title':title,'trigger':f'当前24小时相关信号 {len(hits)} 条；若未来继续增加则提高关注级别','priority':priority,'signals':len(hits),'note':'观察事项，不代表事件必然发生。'})
WATCHLIST.write_text(json.dumps({'updated':stamp,'items':watch},ensure_ascii=False,indent=2),encoding='utf-8')
print(f'wrote {len(uniq)} news, {len(country_rows)} countries, {len(top_events)} timeline events')
