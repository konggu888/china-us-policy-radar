import csv, io, json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
OUT=DATA/'trade_data.json'; HISTORY=DATA/'trade_history.json'; THIRD_COUNTRY=DATA/'third_country_trade.json'
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


THIRD_COUNTRIES={'Vietnam':'5700','Malaysia':'5570','Mexico':'2010','India':'5330','Japan':'5880','Korea':'5800','Thailand':'5490','Germany':'4280'}

def census_hs_sample():
    key=os.environ.get('CENSUS_API_KEY','').strip()
    if not key:
        return {'status':'MISSING','reason':'CENSUS_API_KEY未配置；官方HS API当前要求API key。','source':'U.S. Census Bureau','sourceUrl':'https://www.census.gov/data/developers/data-sets/international-trade.html'}
    year=datetime.now(timezone.utc).year
    month=datetime.now(timezone.utc).month-1
    if month < 1: month=1
    params={'get':'CTY_CODE,CTY_NAME,I_COMMODITY,I_COMMODITY_LDESC,GEN_VAL_MO','time':f'{year}-{month:02d}','CTY_CODE':'5700','key':key}
    url='https://api.census.gov/data/timeseries/intltrade/imports/hs?'+urllib.parse.urlencode(params)
    raw=fetch(url)
    rows=json.loads(raw)
    if not isinstance(rows,list) or len(rows)<2: raise RuntimeError('Census HS API returned no rows')
    head=rows[0]
    return {'status':'OK','period':f'{year}-{month:02d}','partner':'Vietnam','source':'U.S. Census Bureau','sourceUrl':'https://www.census.gov/data/developers/data-sets/international-trade.html','rows':len(rows)-1,'columns':head,'sample':rows[1:21]}

def census_country(country_code):
    url='https://www.census.gov/foreign-trade/balance/c'+str(country_code)+'.html'
    html=fetch(url); text=re.sub(r'<[^>]+>',' ',html); text=re.sub(r'&nbsp;',' ',text); text=re.sub(r'\\s+',' ',text)
    title=re.search(r'Trade in Goods with ([^<]+)',html)
    return {'countryCode':country_code,'source':'U.S. Census Bureau','sourceUrl':url,'available':bool(text),'fetchedAt':datetime.now(timezone.utc).isoformat()}

def main():
    errors=[]; us={}; third={}; hs={}
    try:
        us=census_china()
    except Exception as e:
        errors.append('US_CENSUS:'+str(e))
    try: hs=census_hs_sample()
    except Exception as e: errors.append('HS_API:'+str(e))
    for name,code in THIRD_COUNTRIES.items():
        try:
            third[name]=census_country(code)
        except Exception as e:
            errors.append('THIRD_'+name+':'+str(e))
    payload={'updatedAt':datetime.now(timezone.utc).isoformat(),'usChina':us,'thirdCountry':third,'hs':hs,'chinaCustoms':{'status':'MISSING','reason':'未在本轮写入未经验证的抓取接口；保留缺失状态，避免用二手数据冒充海关原始数据。','sourceUrl':'https://online.customs.gov.cn/'},'quality':{'errors':len(errors),'usChinaStatus':'OK' if us else 'MISSING'}}
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
