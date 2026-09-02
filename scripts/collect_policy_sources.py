import json, re, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; NEWS=DATA/'news.json'
UA='China-US-Global-Intelligence-Radar/PolicySources-1.0'
DOMAINS={
'中国政府网':'gov.cn','国家发展改革委':'ndrc.gov.cn','中国人民银行':'pbc.gov.cn','金融监管总局':'nfra.gov.cn','中国证监会':'csrc.gov.cn','国家外汇局':'safe.gov.cn','工业和信息化部':'miit.gov.cn','科技部':'most.gov.cn','国家能源局':'nea.gov.cn','商务部':'mofcom.gov.cn','海关总署':'customs.gov.cn','外交部':'mfa.gov.cn','国防部':'mod.gov.cn','国家统计局':'stats.gov.cn','财政部':'mof.gov.cn','国家网信办':'cac.gov.cn','新华社':'xinhuanet.com','人民日报':'people.com.cn'}

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=20) as r:return r.read()
def clean(s):return re.sub(r'<[^>]+>|\s+',' ',s or '').strip()
def classify(t):
    rules=[('中美博弈',r'china.?us|us.?china|中美|台海|taiwan|sanction|export control|制裁|出口管制'),('国防',r'military|defen[cs]e|missile|navy|军|导弹|国防'),('外交',r'diplom|foreign|ambassador|外交|大使|峰会'),('贸易 / 供应链',r'trade|tariff|export|import|supply chain|贸易|关税|出口|进口|供应链'),('能源 / 资源',r'energy|oil|gas|lng|electricity|能源|石油|天然气|电力|稀土'),('科技 / AI',r'ai|artificial intelligence|semiconductor|chip|technology|人工智能|半导体|芯片|科技'),('金融',r'bank|central bank|interest|rate|bond|currency|finance|央行|利率|债券|汇率|金融'),('产业',r'industry|manufacturing|factory|industrial|产业|制造|工厂'),('经济',r'economy|gdp|inflation|employment|fiscal|monetary|经济|GDP|通胀|就业|财政|货币'),('国家安全',r'national security|cyber|intelligence|security|国家安全|网络|情报|安全'),('政治',r'government|policy|president|congress|cabinet|政府|政策|总统|国会|内阁')]
    for c,p in rules:
        if re.search(p,t,re.I):return c
    return '全球政策'
def risk(t):
    if re.search(r'war|attack|missile|blockade|nuclear|major sanction|战争|袭击|导弹|封锁|核|重大制裁',t,re.I):return '高'
    if re.search(r'tariff|sanction|military|security|energy|trade|policy|制裁|军事|安全|能源|贸易|政策',t,re.I):return '中'
    return '低'
def query(domain):
    q=urllib.parse.quote('domainis:'+domain)
    url='https://api.gdeltproject.org/api/v2/doc/doc?query='+q+'&mode=artlist&maxrecords=20&format=json&timespan=48h&sort=HybridRel'
    try:obj=json.loads(fetch(url))
    except Exception:return []
    out=[]
    for a in obj.get('articles',[]):
        title=clean(a.get('title')); link=a.get('url') or ''
        if not title:continue
        out.append({'title':title,'url':link,'source':domain,'sourceType':'official','sourceOrg':domain,'sourceTier':'官方','official':True,'verification':'单一官方','time':a.get('seendate','')[:10],'region':'china','cat':classify(title),'risk':risk(title),'x':50,'y':50,'updated':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})
    return out
try:news=json.loads(NEWS.read_text(encoding='utf-8'))
except Exception:news=[]
existing={re.sub(r'[^a-z0-9]','',n.get('title','').lower()) for n in news}
added=0
for _,domain in DOMAINS.items():
    for n in query(domain):
        k=re.sub(r'[^a-z0-9]','',n['title'].lower())
        if k and k not in existing:news.append(n);existing.add(k);added+=1
NEWS.write_text(json.dumps(news[:260],ensure_ascii=False,indent=2),encoding='utf-8')
print('policy source items added:',added)
