import csv, io, json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
MACRO_OUT=DATA/'macro_data.json'
MACRO_HISTORY=DATA/'macro_history.json'
MARKET_OUT=DATA/'market_snapshots.json'
UA='Mozilla/5.0 (compatible; China-US-Global-Intelligence-Radar/Macro-Collector-1.0)'

def fetch(url,timeout=20):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/json,text/csv,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read().decode('utf-8','ignore')

def nfloat(v):
    if v is None:return None
    s=str(v).replace(',','').replace('%','').strip()
    try:return float(s)
    except:return None

def nbs_latest():
    index='https://www.stats.gov.cn/sj/zxfb/'
    html=fetch(index)
    links=re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',html,re.S|re.I)
    candidates=[]
    for href,title in links:
        text=re.sub(r'<[^>]+>','',title).strip()
        if '国民经济运行' in text:
            url=urllib.parse.urljoin(index,href)
            candidates.append((url,text))
    if not candidates:
        raise RuntimeError('NBS latest national-economy release link not found')
    url,title=candidates[0]
    page=fetch(url)
    text=re.sub(r'<script[\s\S]*?</script>',' ',page,flags=re.I)
    text=re.sub(r'<style[\s\S]*?</style>',' ',text,flags=re.I)
    text=re.sub(r'<[^>]+>',' ',text)
    text=re.sub(r'&nbsp;',' ',text)
    text=re.sub(r'\s+',' ',text)
    published=re.search(r'(20\d{2}/\d{1,2}/\d{1,2})',text)
    observed=published.group(1).replace('/','-') if published else ''
    patterns={
      'industrial_yoy_pct':r'规模以上工业增加值[^。]{0,40}?同比(?:实际)?增长\s*([+-]?\d+(?:\.\d+)?)%',
      'industrial_mom_pct':r'规模以上工业增加值[^。]{0,80}?环比(?:增长|上升)\s*([+-]?\d+(?:\.\d+)?)%',
      'services_production_yoy_pct':r'服务业生产指数[^。]{0,40}?同比增长\s*([+-]?\d+(?:\.\d+)?)%',
      'fixed_asset_investment_ytd_yoy_pct':r'固定资产投资[^。]{0,120}?同比下降\s*([+-]?\d+(?:\.\d+)?)%',
      'retail_yoy_pct':r'社会消费品零售总额[^。]{0,120}?同比增长\s*([+-]?\d+(?:\.\d+)?)%',
      'exports_yoy_pct':r'出口(?:额)?[^。]{0,100}?(?:同比)?增长\s*([+-]?\d+(?:\.\d+)?)%',
      'imports_yoy_pct':r'进口(?:额)?[^。]{0,100}?(?:同比)?增长\s*([+-]?\d+(?:\.\d+)?)%',
      'unemployment_pct':r'城镇调查失业率[^。]{0,50}?为\s*([+-]?\d+(?:\.\d+)?)%',
      'cpi_yoy_pct':r'(?:居民消费价格|CPI)[^。]{0,80}?同比上涨\s*([+-]?\d+(?:\.\d+)?)%',
      'cpi_mom_pct':r'(?:居民消费价格|CPI)[^。]{0,100}?环比上涨\s*([+-]?\d+(?:\.\d+)?)%',
      'core_cpi_yoy_pct':r'核心CPI[^。]{0,80}?同比上涨\s*([+-]?\d+(?:\.\d+)?)%',
      'ppi_yoy_pct':r'(?:工业生产者出厂价格|PPI)[^。]{0,100}?同比上涨\s*([+-]?\d+(?:\.\d+)?)%',
      'ppi_mom_pct':r'(?:工业生产者出厂价格|PPI)[^。]{0,100}?环比上涨\s*([+-]?\d+(?:\.\d+)?)%',
      'fx_reserves_usd_trillion':r'外汇储备(?:稳定在|超过|保持在)\s*([+-]?\d+(?:\.\d+)?)万亿美元'
    }
    values={}
    for k,p in patterns.items():
        m=re.search(p,text)
        if m:
            val=nfloat(m.group(1))
            if val is not None: values[k]=val
    return {'source':'国家统计局','sourceUrl':url,'releaseTitle':title,'publishedAt':observed,'fetchedAt':datetime.now(timezone.utc).isoformat(),'values':values,'method':'从国家统计局数据发布页自动发现最新国民经济运行正式发布并解析明确标注的指标；未匹配字段保持缺失。'}

FRED={
 'real_gdp':'GDPC1','cpi':'CPIAUCSL','core_cpi':'CPILFESL','pce_price':'PCEPI',
 'unemployment':'UNRATE','nonfarm_payrolls':'PAYEMS','industrial_production':'INDPRO',
 'retail_sales':'RSAFS','fed_funds':'FEDFUNDS','m2':'M2SL','10y_treasury':'DGS10',
 '2y_treasury':'DGS2','5y_treasury':'DGS5','30y_treasury':'DGS30','usd_index':'DTWEXBGS'
}

def fred_series(series_id):
    url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+urllib.parse.quote(series_id)
    rows=list(csv.DictReader(io.StringIO(fetch(url,25))))
    vals=[]
    for r in rows:
        v=nfloat(r.get(series_id))
        if v is not None:
            vals.append((r.get('observation_date',''),v))
    if not vals: raise RuntimeError('empty FRED '+series_id)
    date,val=vals[-1]
    prev=vals[-2][1] if len(vals)>1 else None
    return {'seriesId':series_id,'observedAt':date,'value':val,'previousValue':prev,'source':'FRED / Federal Reserve Bank of St. Louis','sourceUrl':'https://fred.stlouisfed.org/series/'+series_id}

def collect_us():
    out={}
    errors={}
    for name,sid in FRED.items():
        try: out[name]=fred_series(sid)
        except Exception as e: errors[name]=str(e)
    return out,errors

MARKETS={
 'DXY':'DX-Y.NYB','USD/CNH':'CNH=X','EUR/USD':'EURUSD=X','USD/JPY':'JPY=X',
 '美国2年期收益率':'^IRX','美国5年期收益率':'^FVX','美国10年期收益率':'^TNX','美国30年期收益率':'^TYX',
 'NASDAQ':'^IXIC','道琼斯':'^DJI','恒生指数':'^HSI','恒生科技':'HSTECH.HK','WTI原油':'CL=F','铜':'HG=F','白银':'SI=F',
 '黄金':'GC=F','VIX':'^VIX','标普500':'^GSPC','USD/CNY':'CNY=X'
}

def yahoo(ticker):
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?range=1mo&interval=1d&events=history'
    obj=json.loads(fetch(url,20))
    r=obj['chart']['result'][0]; q=r['indicators']['quote'][0]
    pairs=[(t,c) for t,c in zip(r.get('timestamp',[]),q.get('close',[])) if c is not None]
    if not pairs: raise RuntimeError('empty Yahoo '+ticker)
    closes=[float(x[1]) for x in pairs]
    latest=closes[-1]; prev=closes[-2] if len(closes)>1 else None
    return {'name':None,'ticker':ticker,'value':latest,'change_pct':round((latest/prev-1)*100,4) if prev else None,'observedAt':datetime.fromtimestamp(pairs[-1][0],timezone.utc).strftime('%Y-%m-%d'),'source':'Yahoo Finance','sourceUrl':'https://finance.yahoo.com/quote/'+urllib.parse.quote(ticker)}

def update_market_snapshots():
    try: old=json.loads(MARKET_OUT.read_text(encoding='utf-8'))
    except: old=[]
    if not isinstance(old,list): old=[]
    latest=[]
    for name,ticker in MARKETS.items():
        try:
            x=yahoo(ticker); x['name']=name; latest.append(x)
        except Exception as e:
            print('market missing',name,e)
    # Preserve the existing 9 baseline variables from the prior collector if the expanded provider fails.
    try:
        prior=old[-1].get('markets',[]) if old else []
        by={x.get('name'):x for x in prior}
        for x in latest: by[x['name']]=x
        latest=list(by.values())
    except Exception: pass
    if latest:
        snap={'capturedAt':datetime.now(timezone.utc).isoformat(),'markets':latest}
        # One snapshot per calendar day; replace same-day snapshot instead of duplicating it.
        day=snap['capturedAt'][:10]
        old=[x for x in old if str(x.get('capturedAt',''))[:10]!=day]
        old.append(snap)
        old=old[-730:]
        MARKET_OUT.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
    return len(latest)



NBS_BASE='https://data.stats.gov.cn'
NBS_COOKIE='eyJkZXZpY2UiOiJQQyIsImxhbmd1YWdlIjoiemhfQ04iLCJlbmdpbmUiOiJCbGluayIsImJyb3dzZXIiOiJDaHJvbWUiLCJvcyI6IldpbmRvd3MiLCJwbGF0Zm9ybSI6IldpbjMyIiwiaXNXZWJ2aWV3IjpmYWxzZSwidmVyc2lvbiI6IjE0Ni4wLjAuMCIsImNvcmUiOiJDaHJvbWUiLCJjb3JlVmVyc2lvbiI6IjE0Ni4wLjAuMCJ9'
NBS_HEADERS={'Origin':NBS_BASE,'Referer':NBS_BASE+'/dg/website/page.html#/pc/national/monthData','User-Agent':UA,'Accept':'application/json,text/plain,*/*','Content-Type':'application/json;charset=UTF-8'}

NBS_WANTED=('国内生产总值','GDP','居民消费价格指数','CPI','工业生产者出厂价格指数','PPI','规模以上工业增加值',
 '固定资产投资','社会消费品零售总额','城镇调查失业率','采购经理指数','出口','进口','贸易顺差',
 '房地产开发投资','商品房销售','财政收入','财政支出','广义货币供应量M2','狭义货币供应量M1','人民币贷款','社会融资规模')

def nbs_json(path,params=None,payload=None):
    import urllib.request, json as _json
    url=NBS_BASE+path
    if params:url += '?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers=NBS_HEADERS,method='POST' if payload is not None else 'GET')
    if payload is not None:
        body=_json.dumps(payload,ensure_ascii=False).encode('utf-8')
        req.data=body
    req.add_header('Cookie','client_info='+NBS_COOKIE)
    with urllib.request.urlopen(req,timeout=25) as resp:
        raw=resp.read().decode('utf-8','ignore')
    if raw.lstrip().startswith('<'): raise RuntimeError('NBS structured endpoint returned HTML/challenge')
    return _json.loads(raw)

def nbs_structured():
    page='monthData'
    tree=nbs_json('/dg/website/publicrelease/web/external/new/queryIndexTreeAsync',{'pid':'','code':1}).get('data',[])
    if not tree:return {'status':'MISSING','error':'NBS monthData tree empty'}
    root=tree[0]
    nodes=[root]
    seen=set()
    matched=[]
    while nodes and len(seen)<500:
        node=nodes.pop(0); cid=str(node.get('_id') or '')
        if not cid or cid in seen:continue
        seen.add(cid)
        name=str(node.get('name') or '')
        if any(k in name for k in NBS_WANTED): matched.append({'cid':cid,'name':name})
        children=nbs_json('/dg/website/publicrelease/web/external/new/queryIndexTreeAsync',{'pid':cid,'code':1}).get('data',[])
        nodes.extend(children)
    records=[]
    for cat in matched[:80]:
        inds=nbs_json('/dg/website/publicrelease/web/external/new/queryIndicatorsByCid',{'cid':cat['cid'],'dt':'','name':''}).get('data',{}).get('list',[])
        for ind in inds:
            label=str(ind.get('i_showname') or '').strip()
            if not label or not any(k in label for k in NBS_WANTED):continue
            iid=str(ind.get('_id') or '')
            payload={'cid':cat['cid'],'indicatorIds':[iid],'daCatalogId':'','das':[{'text':'全国','value':'000000000000'}],'showType':2,'dts':[],'rootId':root.get('_id','')}
            raw=nbs_json('/dg/website/publicrelease/web/external/stream/esData',payload=payload)
            for period in raw.get('data',[])[-36:]:
                for item in period.get('values',[]):
                    val=item.get('dataValue',item.get('value',item.get('data_value')))
                    if val in (None,''):continue
                    records.append({'indicatorId':iid,'indicator':label,'category':cat['name'],'period':period.get('code',''),'value':nfloat(val),'unit':ind.get('du_name',ind.get('du','')),'source':'国家统计局国家数据','sourceUrl':NBS_BASE+'/dg/website/page.html#/pc/national/monthData'})
    return {'status':'OK' if records else 'MISSING','fetchedAt':datetime.now(timezone.utc).isoformat(),'records':records,'matchedCategories':matched,'method':'国家统计局新版国家数据公开接口；按指标名称发现并读取月度全国序列，未命中的指标保持缺失。'}



def pbc_latest():
    out={'source':'中国人民银行','fetchedAt':datetime.now(timezone.utc).isoformat(),'records':[],'errors':[]}
    def clean(s):
        s=re.sub(r'<script[\s\S]*?</script>',' ',s,flags=re.I)
        s=re.sub(r'<style[\s\S]*?</style>',' ',s,flags=re.I)
        s=re.sub(r'<[^>]+>',' ',s)
        return re.sub(r'\s+',' ',s).strip()
    def add(url,text,published=''):
        patterns={
          'M2_balance_trillion':r'广义货币\(M2\)余额([0-9.]+)万亿元',
          'M2_yoy_pct':r'广义货币(?:\(M2\))?.*?同比增长([+-]?[0-9.]+)%',
          'M1_balance_trillion':r'狭义货币(?:\(M1\))?余额([0-9.]+)万亿元',
          'M1_yoy_pct':r'狭义货币(?:\(M1\))?.*?同比增长([+-]?[0-9.]+)%',
          'M0_balance_trillion':r'流通中货币(?:\(M0\))?余额([0-9.]+)万亿元',
          'RMB_loans_balance_trillion':r'人民币贷款余额([0-9.]+)万亿元',
          'RMB_loans_ytd_trillion':r'前([一二三四五六七八九十0-9]+)个月人民币贷款增加([0-9.]+)万亿元',
          'RMB_deposits_balance_trillion':r'人民币存款余额([0-9.]+)万亿元',
          'RMB_deposits_ytd_trillion':r'前([一二三四五六七八九十0-9]+)个月人民币存款增加([0-9.]+)万亿元',
          'interbank_lending_rate_pct':r'同业拆借月加权平均利率为([0-9.]+)%',
          'pledged_repo_rate_pct':r'质押式(?:债券)?回购月加权平均利率为([0-9.]+)%',
          'social_financing_ytd_trillion':r'社会融资规模增量累计为([0-9.]+)万亿元'
        }
        found=0
        for name,pat in patterns.items():
            m=re.search(pat,text)
            if m:
                out['records'].append({'indicator':name,'value':nfloat(m.group(1) if name.endswith('_pct') or 'balance' in name or 'ytd' in name or name=='social_financing_ytd_trillion' else m.group(1)),'publishedAt':published,'sourceUrl':url,'source':'中国人民银行'})
                found+=1
        return found
    try:
        index=fetch('https://www.pbc.gov.cn/diaochatongjisi/116219/116225/index.html')
        links=re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',index,re.S|re.I)
        candidates=[]
        for href,title in links:
            txt=clean(title)
            if ('金融统计数据报告' in txt or '社会融资规模增量统计数据报告' in txt or '社会融资规模存量统计数据报告' in txt) and re.search(r'2026年',txt):
                candidates.append((urllib.parse.urljoin('https://www.pbc.gov.cn/',href),txt))
        for url,title in candidates[:12]:
            try:
                body=clean(fetch(url))
                date=re.search(r'文章来源：\s*(20\d{2}-\d{2}-\d{2})',body)
                add(url,body,date.group(1) if date else '')
            except Exception as e: out['errors'].append('REPORT:'+str(e))
    except Exception as e: out['errors'].append('REPORT_INDEX:'+str(e))
    try:
        home=fetch('https://www.pbc.gov.cn/')
        links=re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',home,re.S|re.I)
        for href,title in links:
            txt=clean(title)
            if '公开市场业务交易公告' in txt:
                url=urllib.parse.urljoin('https://www.pbc.gov.cn/',href)
                body=clean(fetch(url))
                m=re.search(r'(20\d{2}-\d{1,2}-\d{1,2}).{0,250}?开展了([0-9.]+)亿元(?:[0-9一二三四五六七八九十]*?)([0-9]+)天期逆回购操作',body)
                if m:
                    out['records'].append({'indicator':'open_market_7d_reverse_repo_amount_billion','value':nfloat(m.group(2)),'observedAt':m.group(1),'source':'中国人民银行','sourceUrl':url})
                break
    except Exception as e: out['errors'].append('OMO:'+str(e))
    try:
        html=fetch('https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do')
        plain=clean(html)
        m=re.search(r'(20\d{2}-\d{2}-\d{2})\s+([0-9]+(?:\.[0-9]+)?)',plain)
        if m: out['records'].append({'indicator':'USD/CNY_PBOC_MID','value':nfloat(m.group(2))/100,'observedAt':m.group(1),'source':'SAFE/PBOC RMB central parity','sourceUrl':'https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do'})
    except Exception as e: out['errors'].append('RMB_MID:'+str(e))
    out['status']='OK' if out['records'] else 'MISSING'
    return out

def main():
    errors=[]
    try: pbc=pbc_latest()
    except Exception as e:
        pbc={'status':'MISSING','records':[],'errors':[str(e)]}; errors.append('PBC:'+str(e))
    try: nbs=nbs_structured()
    except Exception as e:
        nbs={'status':'MISSING','error':str(e),'records':[]}; errors.append('NBS_STRUCTURED:'+str(e))
    try: cn=nbs_latest()
    except Exception as e:
        cn={'source':'国家统计局','status':'MISSING','error':str(e),'method':'官方源暂未成功获取；不使用其他来源冒充。'}; errors.append('NBS:'+str(e))
    us,us_errors=collect_us()
    if us_errors: errors.extend('FRED '+k+':'+v for k,v in us_errors.items())
    market_count=update_market_snapshots()
    payload={'updatedAt':datetime.now(timezone.utc).isoformat(),'china':cn,'chinaStructured':nbs,'pbc':pbc,'unitedStates':{'source':'FRED','series':us,'errors':us_errors,'apiMode':'public fredgraph CSV; no API key'},'marketSnapshotCount':market_count,'quality':{'chinaStatus':'OK' if cn.get('values') else 'MISSING','usSeriesCount':len(us),'marketVariableCount':market_count,'errors':len(errors)}}
    MACRO_OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    # Keep immutable daily macro observations; never overwrite an earlier day with current data.
    try:
        history=json.loads(MACRO_HISTORY.read_text(encoding='utf-8')) if MACRO_HISTORY.exists() else []
        if not isinstance(history,list): history=[]
        day=payload['updatedAt'][:10]
        history=[x for x in history if str(x.get('updatedAt',''))[:10]!=day]
        history.append(payload)
        history=history[-730:]
        MACRO_HISTORY.write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception as e:
        print('macro history warning',type(e).__name__)
    print('macro: China',len(cn.get('values',{})),'US',len(us),'market',market_count,'errors',len(errors))
    # Do not fail the entire pipeline for a single upstream series; fail only if both macro sides and markets are empty.
    if not cn.get('values') and nbs.get('status')!='OK' and not us and market_count==0:return 1
    return 0

if __name__=='__main__':
    sys.exit(main())
