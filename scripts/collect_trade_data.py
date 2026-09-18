import csv, io, json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
OUT=DATA/'trade_data.json'; HISTORY=DATA/'trade_history.json'
UA='Mozilla/5.0 (compatible; China-US-Global-Intelligence-Radar/Trade-Collector-1.0)'

def fetch(url, timeout=30):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/json,text/csv,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read().decode('utf-8','ignore')

def num(v):
    try:return float(str(v).replace(',','').strip())
    except:return None

def census_china():
    url='https://www.census.gov/foreign-trade/balance/c5700.html'
    html=fetch(url)
    text=re.sub(r'<[^>]+>',' ',html); text=re.sub(r'&nbsp;',' ',text); text=re.sub(r'\s+',' ',text)
    m=re.search(r'2026.*?January 2026\s+([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+).*?TOTAL 2026\s+([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)',text)
    if not m: raise RuntimeError('Census China trade table not parsed')
    vals=[num(x) for x in m.groups()]
    return {'source':'U.S. Census Bureau','sourceUrl':url,'unit':'USD million','basis':'nominal, not seasonally adjusted','year':2026,'ytd':{'exports':vals[3],'imports':vals[4],'balance':vals[5]},'jan':{'exports':vals[0],'imports':vals[1],'balance':vals[2]},'fetchedAt':datetime.now(timezone.utc).isoformat()}

def main():
    errors=[]; us={}
    try: us=census_china()
    except Exception as e: errors.append('US_CENSUS:'+str(e))
    payload={'updatedAt':datetime.now(timezone.utc).isoformat(),'usChina':us,'chinaCustoms':{'status':'MISSING','reason':'未在本轮写入未经验证的抓取接口；保留缺失状态，避免用二手数据冒充海关原始数据。','sourceUrl':'https://online.customs.gov.cn/'},'quality':{'errors':len(errors),'usChinaStatus':'OK' if us else 'MISSING'}}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        history=json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else []
        if not isinstance(history,list):history=[]
        day=payload['updatedAt'][:10]; history=[x for x in history if str(x.get('updatedAt',''))[:10]!=day]
        history.append(payload); HISTORY.write_text(json.dumps(history[-730:],ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception as e: print('trade history warning',type(e).__name__)
    print('trade: US-China',bool(us),'errors',len(errors))
    return 0 if us else 1

if __name__=='__main__':sys.exit(main())
