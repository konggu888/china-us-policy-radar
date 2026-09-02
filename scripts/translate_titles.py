import json,re,urllib.parse,urllib.request,time
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'data/news.json'
try: data=json.loads(P.read_text(encoding='utf-8'))
except Exception: data=[]
UA='China-US-Global-Intelligence-Radar/TitleTranslator-1.0'
def is_english(s):
 return bool(re.search(r'[A-Za-z]{4,}',s)) and not re.search(r'[\u4e00-\u9fff]',s)
def translate(s):
 url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode({'client':'gtx','sl':'en','tl':'zh-CN','dt':'t','q':s[:450]})
 try:
  req=urllib.request.Request(url,headers={'User-Agent':UA})
  raw=urllib.request.urlopen(req,timeout=8).read().decode('utf-8')
  obj=json.loads(raw); return ''.join(x[0] for x in obj[0] if x and x[0]).strip()
 except Exception:return ''
cache={}
for n in data:
 s=n.get('title','')
 if n.get('region')!='us' or not is_english(s):
  if not n.get('titleZh') and not is_english(s): n['titleZh']=s
  continue
 if s in cache:n['titleZh']=cache[s];continue
 z=translate(s); cache[s]=z
 if z:n['titleZh']=z
 time.sleep(0.08)
P.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('translated',sum(1 for n in data if n.get('titleZh') and n.get('titleZh')!=n.get('title','')),'US titles; fallback keeps original when translation unavailable')
