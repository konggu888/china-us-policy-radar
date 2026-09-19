import csv, io, json, re, sys, urllib.parse, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
OUT=DATA/'trade_data.json'; HISTORY=DATA/'trade_history.json'; THIRD_COUNTRY=DATA/'third_country_trade.json'; FOCUS_MAP=DATA/'trade_focus_map.json'
UA='Mozilla/5.0 (compatible; China-US-Global-Intelligence-Radar/Trade-Collector-1.0)'

def fetch(url, timeout=30):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/json,text/csv,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read().decode('utf-8','ignore')

def load_focus_map():
    try:
        x=json.loads(FOCUS_MAP.read_text(encoding='utf-8'))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}


def census_zip_bytes(year,month):
    yy=str(year)[-2:]; mm=f'{month:02d}'
    url=f'https://www.census.gov/trade/downloads/{year}/Merch/im_m/IMDB{yy}{mm}.ZIP'
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/zip,application/octet-stream,*/*'})
    with urllib.request.urlopen(req,timeout=90) as r:
        return url,r.read()

def latest_available_census_month():
    now=datetime.now(timezone.utc)
    for offset in range(0,4):
        y=now.year; m=now.month-offset
        while m<=0: y-=1; m+=12
        try:
            url,raw=census_zip_bytes(y,m)
            return y,m,url,raw
        except Exception:
            continue
    raise RuntimeError('No recent Census merchandise import ZIP available')

def parse_focus_trade(year,month,raw,focus,country_codes):
    sectors=focus.get('sectors',[]) if isinstance(focus,dict) else []
    prefixes=sorted({str(p) for s in sectors for p in s.get('hsPrefixes',[])},key=len,reverse=True)
    wanted={str(k) for k in country_codes}
    agg={}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name=next((n for n in z.namelist() if n.upper().endswith('IMP_DETL.TXT')),None)
        if not name: raise RuntimeError('IMP_DETL.TXT missing from Census ZIP')
        with z.open(name) as fh:
            for rawline in fh:
                line=rawline.decode('latin-1','ignore').rstrip('\\r\\n')
                if len(line)<688: continue
                hs=line[0:10].strip(); country=line[10:14].strip()
                if country not in wanted or not any(hs.startswith(p) for p in prefixes): continue
                value=num(line[73:88])
                if value is None: continue
                for s in sectors:
                    if any(hs.startswith(str(p)) for p in s.get('hsPrefixes',[])):
                        key=(s.get('id'),country)
                        agg[key]=agg.get(key,0.0)+value
    return [{'sector':sid,'countryCode':country,'period':f'{year}-{month:02d}','importsForConsumptionUsd':round(value,2)}
            for (sid,country),value in sorted(agg.items())]

def num(v):
    try:return float(str(v).replace(',','').strip())
    except:return None

def census_china():
    url='https://www.census.gov/foreign-trade/balance/c5700.html'
    html=fetch(url)
    text=re.sub(r'<[^>]+>',' ',html); text=re.sub(r'&nbsp;',' ',text); text=re.sub(r'\s+',' ',text)
    m=re.search(r'TOTAL\s+20\d{2}\s+([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)',text)
    if not m: raise RuntimeError('Census China trade table not parsed')
    vals=[num(x) for x in m.groups()]
    return {'source':'U.S. Census Bureau','sourceUrl':url,'unit':'USD million','basis':'nominal, not seasonally adjusted','year':datetime.now(timezone.utc).year,'ytd':{'exports':vals[0],'imports':vals[1],'balance':vals[2]},'fetchedAt':datetime.now(timezone.utc).isoformat()}


THIRD_COUNTRIES={'Vietnam':'5700','Malaysia':'5570','Mexico':'2010','India':'5330','Japan':'5880','Korea':'5800','Thailand':'5490','Germany':'4280'}

def census_country(country_code):
    url='https://www.census.gov/foreign-trade/balance/c'+str(country_code)+'.html'
    html=fetch(url); text=re.sub(r'<[^>]+>',' ',html); text=re.sub(r'&nbsp;',' ',text); text=re.sub(r'\\s+',' ',text)
    title=re.search(r'Trade in Goods with ([^<]+)',html)
    return {'countryCode':country_code,'source':'U.S. Census Bureau','sourceUrl':url,'available':bool(text),'fetchedAt':datetime.now(timezone.utc).isoformat()}

def main():
    errors=[]; us={}; third={}; focus=load_focus_map(); focus_trade={}
    try:
        us=census_china()
    except Exception as e:
        errors.append('US_CENSUS:'+str(e))
    for name,code in THIRD_COUNTRIES.items():
        try:
            third[name]=census_country(code)
        except Exception as e:
            errors.append('THIRD_'+name+':'+str(e))
    try:
        y,m,zip_url,zip_raw=latest_available_census_month()
        country_codes={'China':'5700',**THIRD_COUNTRIES}
        rows=parse_focus_trade(y,m,zip_raw,focus,country_codes.values())
        focus_trade={'status':'OK','period':f'{y}-{m:02d}','source':'U.S. Census Bureau','sourceUrl':zip_url,'rows':rows,'countryCount':len(country_codes)}
    except Exception as e:
        errors.append('FOCUS_TRADE:'+str(e))
        focus_trade={'status':'MISSING','reason':str(e)}
    payload={'updatedAt':datetime.now(timezone.utc).isoformat(),'focusMapVersion':focus.get('version'),'focusSectorCount':len(focus.get('sectors',[])),'focusTrade':focus_trade,'usChina':us,'thirdCountry':third,'chinaCustoms':{'status':'MISSING','reason':'未在本轮写入未经验证的抓取接口；保留缺失状态，避免用二手数据冒充海关原始数据。','sourceUrl':'https://online.customs.gov.cn/'},'quality':{'errors':len(errors),'errorDetails':errors,'usChinaStatus':'OK' if us else 'MISSING','focusTradeStatus':focus_trade.get('status'),'thirdCountryCount':len(third)}}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        history=json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else []
        if not isinstance(history,list):history=[]
        day=payload['updatedAt'][:10]; history=[x for x in history if str(x.get('updatedAt',''))[:10]!=day]
        history.append(payload); HISTORY.write_text(json.dumps(history[-730:],ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception as e: print('trade history warning',type(e).__name__)
    print('trade: US-China',bool(us),'errors',len(errors))
    return 0 if (us or focus_trade.get('status')=='OK' or len(third)>=3) else 1

if __name__=='__main__':sys.exit(main())
