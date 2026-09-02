import json,re,urllib.parse,urllib.request,time
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'data/news.json'
try: data=json.loads(P.read_text(encoding='utf-8'))
except Exception: data=[]
UA='China-US-Global-Intelligence-Radar/TitleTranslator-2.0'
def is_english(s): return bool(re.search(r'[A-Za-z]{4,}',s)) and not re.search(r'[\u4e00-\u9fff]',s)
def google_translate(s):
 url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode({'client':'gtx','sl':'en','tl':'zh-CN','dt':'t','q':s[:450]})
 try:
  req=urllib.request.Request(url,headers={'User-Agent':UA}); raw=urllib.request.urlopen(req,timeout=12).read().decode('utf-8'); obj=json.loads(raw)
  z=''.join(x[0] for x in obj[0] if x and x[0]).strip(); return z if z and z!=s else ''
 except Exception:return ''
def mymemory_translate(s):
 url='https://api.mymemory.translated.net/get?'+urllib.parse.urlencode({'q':s[:450],'langpair':'en|zh-CN'})
 try:
  req=urllib.request.Request(url,headers={'User-Agent':UA}); obj=json.loads(urllib.request.urlopen(req,timeout=12).read().decode('utf-8'))
  z=((obj.get('responseData') or {}).get('translatedText') or '').strip()
  if z and z.lower()!=s.lower(): return z
 except Exception: pass
 return ''
def translate(s): return google_translate(s) or mymemory_translate(s)
cache={}; translated=0
for n in data:
 s=(n.get('title') or '').strip()
 if n.get('region')!='us' or not is_english(s):
  if not n.get('titleZh'): n['titleZh']=s
  continue
 if s in cache: z=cache[s]
 else: z=translate(s); cache[s]=z; time.sleep(0.12)
 if z: n['titleZh']=z; translated+=1
 else: n['titleZh']=s
P.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('translated',translated,'US titles; untranslated titles explicitly fall back to original')