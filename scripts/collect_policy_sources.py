import json,re,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; NEWS=DATA/'news.json'
UA='China-US-Global-Intelligence-Radar/PolicySources-2.0'
# First-party domains. Discovery is attempted independently of GDELT/media discovery.
DOMAINS={
'中国政府网':'gov.cn','国家发展改革委':'ndrc.gov.cn','中国人民银行':'pbc.gov.cn','金融监管总局':'nfra.gov.cn','中国证监会':'csrc.gov.cn','国家外汇局':'safe.gov.cn','工业和信息化部':'miit.gov.cn','科技部':'most.gov.cn','国家能源局':'nea.gov.cn','商务部':'mofcom.gov.cn','海关总署':'customs.gov.cn','外交部':'mfa.gov.cn','国防部':'mod.gov.cn','国家统计局':'stats.gov.cn','财政部':'mof.gov.cn','国家网信办':'cac.gov.cn',
'White House':'whitehouse.gov','US State Department':'state.gov','US Defense Department':'defense.gov','US Treasury':'treasury.gov','Federal Reserve':'federalreserve.gov','US Commerce':'commerce.gov','USTR':'ustr.gov','US Energy':'energy.gov','EIA':'eia.gov','BLS':'bls.gov','BEA':'bea.gov','NIST':'nist.gov','Congress':'congress.gov',
'United Nations':'un.org','WTO':'wto.org','IMF':'imf.org','World Bank':'worldbank.org','IEA':'iea.org','OECD':'oecd.org','BIS':'bis.org','IAEA':'iaea.org'}
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json,text/html,application/xhtml+xml,*/*'})
 with urllib.request.urlopen(req,timeout=20) as r:return r.read()
def clean(s):return re.sub(r'<[^>]+>|\s+',' ',s or '').strip()
def classify(t):
 rules=[('中美博弈',r'china.?us|us.?china|中美|台海|taiwan|sanction|export control|制裁|出口管制'),('国防',r'military|defen[cs]e|missile|navy|army|air force|国防|军事|导弹|海军|空军'),('外交',r'diplom|foreign|ambassador|summit|外交|大使|峰会'),('贸易 / 供应链',r'trade|tariff|export|import|supply chain|贸易|关税|出口|进口|供应链'),('能源 / 资源',r'energy|oil|gas|lng|electricity|uranium|rare earth|能源|石油|天然气|电力|铀|稀土'),('科技 / AI',r'ai|artificial intelligence|semiconductor|chip|technology|人工智能|半导体|芯片|科技'),('金融',r'bank|central bank|interest|rate|bond|currency|finance|央行|利率|债券|汇率|金融'),('产业',r'industry|manufacturing|factory|industrial|产业|制造|工厂'),('经济',r'economy|gdp|inflation|employment|fiscal|monetary|经济|GDP|通胀|就业|财政|货币'),('国家安全',r'national security|cyber|intelligence|security|国家安全|网络|情报|安全'),('内政',r'domestic|immigration|border|healthcare|housing|education|内政|移民|边境|医疗|住房|教育'),('政治',r'government|policy|president|congress|cabinet|election|政府|政策|总统|国会|内阁|选举')]
 for c,p in rules:
  if re.search(p,t,re.I):return c
 return '全球政策'
def risk(t):
 if re.search(r'war|attack|missile|blockade|nuclear|major sanction|战争|袭击|导弹|封锁|核|重大制裁',t,re.I):return '高'
 if re.search(r'tariff|sanction|military|security|energy|trade|policy|制裁|军事|安全|能源|贸易|政策',t,re.I):return '中'
 return '低'
def query(domain,org):
 q=urllib.parse.quote('domainis:'+domain)
 url='https://api.gdeltproject.org/api/v2/doc/doc?query='+q+'&mode=artlist&maxrecords=30&format=json&timespan=72h&sort=HybridRel'
 try:obj=json.loads(fetch(url))
 except Exception:return []
 region='us' if domain in {'whitehouse.gov','state.gov','defense.gov','treasury.gov','federalreserve.gov','commerce.gov','ustr.gov','energy.gov','eia.gov','bls.gov','bea.gov','nist.gov','congress.gov'} else ('global' if domain in {'un.org','wto.org','imf.org','worldbank.org','iea.org','oecd.org','bis.org','iaea.org'} else 'china')
 out=[]
 for a in obj.get('articles',[]):
  title=clean(a.get('title')); link=a.get('url') or ''
  if not title or not link:continue
  out.append({'title':title,'url':link,'source':org,'sourceType':'official','sourceOrg':org,'sourceTier':'官方' if region!='global' else '国际机构','official':True,'verification':'单一官方','time':a.get('seendate','')[:10],'region':region,'cat':classify(title),'risk':risk(title),'x':50,'y':50,'updated':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})
 return out
try:news=json.loads(NEWS.read_text(encoding='utf-8'))
except Exception:news=[]
existing={(n.get('url') or '').strip() for n in news}; added=0
for org,domain in DOMAINS.items():
 for n in query(domain,org):
  if n['url'] not in existing:news.append(n);existing.add(n['url']);added+=1
NEWS.write_text(json.dumps(news,ensure_ascii=False,indent=2),encoding='utf-8')
print('first-party/institution items added:',added,'total working items:',len(news))