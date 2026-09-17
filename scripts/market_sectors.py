import json, urllib.parse, urllib.request, time, re
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'market_sectors.json'
UA='Mozilla/5.0 (compatible; China-US-Global-Intelligence-Radar/Market-Collector-4.0)'
SECTORS={'科技':'XLK','金融':'XLF','能源':'XLE','工业':'XLI','可选消费':'XLY','必选消费':'XLP','医疗':'XLV','材料':'XLB','房地产':'XLRE','通信服务':'XLC','公用事业':'XLU'}
A_SHARE={'上证指数':'000001.SS','深证成指':'399001.SZ','沪深300':'000300.SS','中证500':'000905.SS','中证1000':'000852.SS','创业板指':'399006.SZ','科创50':'000688.SS'}
TENCENT={'000001.SS':'sh000001','399001.SZ':'sz399001','000300.SS':'sh000300','000905.SS':'sh000905','000852.SS':'sh000852','399006.SZ':'sz399006','000688.SS':'sh000688'}
EM_HOSTS=['https://17.push2.eastmoney.com/api/qt/clist/get','https://push2.eastmoney.com/api/qt/clist/get']
EM_KLINE='https://push2his.eastmoney.com/api/qt/stock/kline/get'; UT='bd1d9ddb04089700cf9c27f6f7426281'

def fetch(url,timeout=15,referer='https://finance.yahoo.com/'):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Referer':referer,'Accept':'application/json,text/plain,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode('utf-8','ignore')

def yahoo(ticker):
    for host in ('query1.finance.yahoo.com','query2.finance.yahoo.com'):
        try:
            url=f'https://{host}/v8/finance/chart/{urllib.parse.quote(ticker)}?range=1y&interval=1d&events=history'
            obj=json.loads(fetch(url)); r=obj['chart']['result'][0]; q=r['indicators']['quote'][0]; pairs=[(ts,c) for ts,c in zip(r.get('timestamp',[]),q.get('close',[])) if c is not None]
            if len(pairs)<2:continue
            closes=[float(c) for _,c in pairs]; ts=[t for t,_ in pairs]; now=closes[-1]
            def ret(days):return None if len(closes)<=days else round((now/closes[-days-1]-1)*100,2)
            return {'ticker':ticker,'latest':round(now,4),'daily_pct':ret(1),'weekly_pct':ret(5),'monthly_pct':ret(21),'quarterly_pct':ret(63),'six_month_pct':round((now/closes[max(0,len(closes)-126)]-1)*100,2),'asof':datetime.fromtimestamp(ts[-1],timezone.utc).strftime('%Y-%m-%d'),'provider':'Yahoo Finance'}
        except Exception:continue
    return None

def tencent_index(ticker):
    code=TENCENT.get(ticker)
    if not code:return None
    try:
        s=fetch('https://qt.gtimg.cn/q='+code,10,'https://gu.qq.com/')
        # v_sh000001="1~上证指数~000001~...~最新~...~涨跌额~涨跌幅~...~日期~时间~..."
        m=re.search(r'="(.*?)"',s)
        if not m:return None
        p=m.group(1).split('~')
        latest=float(p[3]); prev=float(p[4]); change_pct=(latest/prev-1)*100 if prev else None
        date=p[30] if len(p)>30 and re.fullmatch(r'\d{4}/\d{2}/\d{2}',p[30] or '') else datetime.now(timezone.utc).strftime('%Y-%m-%d')
        return {'ticker':ticker,'latest':latest,'daily_pct':round(change_pct,2) if change_pct is not None else None,'weekly_pct':None,'monthly_pct':None,'quarterly_pct':None,'six_month_pct':None,'asof':date.replace('/','-'),'provider':'Tencent quote fallback','fallback':True}
    except Exception:return None

def get(ticker):
    return yahoo(ticker) or tencent_index(ticker)

def eastmoney_boards():
    params={'pn':'1','pz':'100','po':'1','np':'1','ut':UT,'fltt':'2','invt':'2','fid':'f3','fs':'m:90+t:2+f:!50','fields':'f12,f14,f2,f3,f4,f104,f105,f128'}; last='error:HTTPError'
    for host in EM_HOSTS:
        try:
            obj=json.loads(fetch(host+'?'+urllib.parse.urlencode(params),20,'https://data.eastmoney.com/')); rows=obj.get('data',{}).get('diff',[]) or []; out=[]
            for x in rows:
                try:p=float(x.get('f3'))
                except Exception:continue
                name=str(x.get('f14') or '').strip(); code=str(x.get('f12') or '').strip()
                if name and code:out.append({'code':code,'name':name,'change_pct':round(p,2),'price':x.get('f2'),'change':x.get('f4'),'up_count':x.get('f104'),'down_count':x.get('f105'),'leader':x.get('f128') or ''})
            if out:
                out.sort(key=lambda x:x['change_pct'],reverse=True); return out,'ok'
        except Exception as e:last=f'error:{type(e).__name__}'
    return [],last

def board_weekly_pct(code):
    params={'secid':f'90.{code}','fields1':'f1,f2,f3,f4,f5,f6','fields2':'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61','klt':'101','fqt':'1','beg':'0','end':'20500101','lmt':'20','ut':UT}
    try:
        obj=json.loads(fetch(EM_KLINE+'?'+urllib.parse.urlencode(params),12,'https://quote.eastmoney.com/')); rows=obj.get('data',{}).get('klines',[]) or []
        parsed=[]
        for row in rows:
            parts=row.split(',')
            if len(parts)>=3:
                try:parsed.append((datetime.strptime(parts[0],'%Y-%m-%d').date(),float(parts[2])))
                except Exception:pass
        if len(parsed)<2:return None,None,None
        latest_date,latest=parsed[-1]; current_week=latest_date.isocalendar()[:2]; first_idx=next((i for i,(d,_) in enumerate(parsed) if d.isocalendar()[:2]==current_week),len(parsed)-1)
        if first_idx==0:return None,parsed[first_idx][0].isoformat(),latest_date.isoformat()
        base_date,base=parsed[first_idx-1]
        return (round((latest/base-1)*100,2) if base else None),base_date.isoformat(),latest_date.isoformat()
    except Exception:return None,None,None

us={}
for name,t in SECTORS.items():
    v=get(t)
    if v:us[name]=v
    time.sleep(.08)
a_share={}
for name,t in A_SHARE.items():
    v=get(t)
    if v:a_share[name]=v
    time.sleep(.08)
# Tencent supplies the current quote when Yahoo is unavailable; keep the previous weekly/monthly value if possible.
try:old=json.loads(OUT.read_text(encoding='utf-8'))
except Exception:old={}
old_a=old.get('a_share',{}) if isinstance(old,dict) else {}
for name,v in a_share.items():
    if v.get('weekly_pct') is None and name in old_a:
        for k in ('weekly_pct','monthly_pct','quarterly_pct','six_month_pct'):
            if old_a[name].get(k) is not None:v[k]=old_a[name][k]
rank=sorted(us.items(),key=lambda kv:kv[1].get('weekly_pct') if kv[1].get('weekly_pct') is not None else -999,reverse=True)
for i,(name,v) in enumerate(rank,1):v['weekly_rank']=i
arank=sorted(a_share.items(),key=lambda kv:kv[1].get('weekly_pct') if kv[1].get('weekly_pct') is not None else -999,reverse=True)
for i,(name,v) in enumerate(arank,1):v['weekly_rank']=i
boards,status=eastmoney_boards(); weekly_boards=[]
for b in boards:
    wp,week_start,week_end=board_weekly_pct(b['code'])
    if wp is not None:
        x=dict(b);x['weekly_pct']=wp;x['weekly_period_start']=week_start;x['weekly_period_end']=week_end;weekly_boards.append(x)
    time.sleep(.05)
weekly_boards.sort(key=lambda x:x['weekly_pct'],reverse=True)
positive=[x for x in weekly_boards if x['weekly_pct']>0];negative=[x for x in weekly_boards if x['weekly_pct']<0]
now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
payload={'updated':now,'method':'Yahoo Finance with Tencent quote fallback for A-share indices + Eastmoney industry boards; no API token required','providers':{'us_sector':'Yahoo Finance public chart endpoint','a_share_index':'Yahoo Finance -> Tencent quote fallback','a_share_industry':'Eastmoney public quote/K-line endpoints'},'sectors':us,'a_share':a_share,'a_share_industry_boards':boards,'a_share_board_status':status,'a_share_weekly_industry_boards':weekly_boards,'weekly_risers':[n for n,v in rank if (v.get('weekly_pct') or 0)>0],'weekly_fallers':[n for n,v in reversed(rank) if (v.get('weekly_pct') or 0)<0],'a_share_weekly_risers':positive[:10],'a_share_weekly_fallers':list(reversed(negative[-10:])), 'a_share_board_risers':[x['name'] for x in boards[:5]],'a_share_board_fallers':[x['name'] for x in boards[-5:][::-1]],'health':{'us_sector_count':len(us),'a_share_index_count':len(a_share),'a_share_board_count':len(boards),'weekly_board_count':len(weekly_boards),'status':'ok' if len(a_share)>=5 and len(us)>=8 else 'partial'}}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print('market sectors:',len(us),'A-share indices:',len(a_share),'A-share industry boards:',len(boards),'weekly boards:',len(weekly_boards),'status:',payload['health']['status'])
