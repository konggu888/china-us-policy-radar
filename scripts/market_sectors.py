import json, urllib.parse, urllib.request, time
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'market_sectors.json'
UA='Mozilla/5.0 (compatible; China-US-Global-Intelligence-Radar/Market-Collector-3.1)'
SECTORS={'科技':'XLK','金融':'XLF','能源':'XLE','工业':'XLI','可选消费':'XLY','必选消费':'XLP','医疗':'XLV','材料':'XLB','房地产':'XLRE','通信服务':'XLC','公用事业':'XLU'}
A_SHARE={'上证指数':'000001.SS','深证成指':'399001.SZ','沪深300':'000300.SS','中证500':'000905.SS','中证1000':'000852.SS','创业板指':'399006.SZ','科创50':'000688.SS'}
EM='https://push2.eastmoney.com/api/qt/clist/get'
EM_HOSTS=['https://17.push2.eastmoney.com/api/qt/clist/get','https://push2.eastmoney.com/api/qt/clist/get']
EM_KLINE='https://push2his.eastmoney.com/api/qt/stock/kline/get'
UT='bd1d9ddb04089700cf9c27f6f7426281'

def get(ticker):
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?range=6mo&interval=1d'
    try:
        req=urllib.request.Request(url,headers={'User-Agent':UA}); obj=json.loads(urllib.request.urlopen(req,timeout=15).read().decode())
        r=obj['chart']['result'][0]; q=r['indicators']['quote'][0]; closes=[x for x in q['close'] if x is not None]; ts=[x for x,c in zip(r['timestamp'],q['close']) if c is not None]
        if len(closes)<2:return None
        now=closes[-1]
        def ret(days): return None if len(closes)<=days else round((now/closes[-days-1]-1)*100,2)
        return {'ticker':ticker,'latest':round(now,4),'daily_pct':ret(1),'weekly_pct':ret(5),'monthly_pct':ret(21),'quarterly_pct':ret(63),'six_month_pct':round((now/closes[0]-1)*100,2),'asof':datetime.fromtimestamp(ts[-1],timezone.utc).strftime('%Y-%m-%d')}
    except Exception:return None

def eastmoney_boards():
    params={'pn':'1','pz':'100','po':'1','np':'1','ut':UT,'fltt':'2','invt':'2','fid':'f3','fs':'m:90+t:2+f:!50','fields':'f12,f14,f2,f3,f4,f104,f105,f128'}
    last='error:HTTPError'
    for host in EM_HOSTS:
        try:
            req=urllib.request.Request(host+'?'+urllib.parse.urlencode(params),headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'})
            obj=json.loads(urllib.request.urlopen(req,timeout=20).read().decode('utf-8','ignore')); rows=obj.get('data',{}).get('diff',[]) or []
            out=[]
            for x in rows:
                try:p=float(x.get('f3'))
                except Exception:continue
                name=str(x.get('f14') or '').strip()
                code=str(x.get('f12') or '').strip()
                if not name or not code:continue
                out.append({'code':code,'name':name,'change_pct':round(p,2),'price':x.get('f2'),'change':x.get('f4'),'up_count':x.get('f104'),'down_count':x.get('f105'),'leader':x.get('f128') or ''})
            out.sort(key=lambda x:x['change_pct'],reverse=True)
            return out,'ok'
        except Exception as e:last=f'error:{type(e).__name__}'
    return [],last

def board_weekly_pct(code):
    params={'secid':f'90.{code}','fields1':'f1,f2,f3,f4,f5,f6','fields2':'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61','klt':'102','fqt':'1','beg':'0','end':'20500101','lmt':'2','ut':UT}
    try:
        req=urllib.request.Request(EM_KLINE+'?'+urllib.parse.urlencode(params),headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'})
        obj=json.loads(urllib.request.urlopen(req,timeout=12).read().decode('utf-8','ignore')); rows=obj.get('data',{}).get('klines',[]) or []
        if not rows:return None,None
        vals=rows[-1].split(',')
        if len(vals)<4:return None,None
        op=float(vals[1]); close=float(vals[2]);
        if op==0:return None,vals[0]
        return round((close/op-1)*100,2),vals[0]
    except Exception:return None,None

us={}
for name,t in SECTORS.items():
    v=get(t)
    if v:us[name]=v
    time.sleep(.1)
a_share={}
for name,t in A_SHARE.items():
    v=get(t)
    if v:a_share[name]=v
    time.sleep(.1)
rank=sorted(us.items(),key=lambda kv:kv[1].get('weekly_pct') if kv[1].get('weekly_pct') is not None else -999,reverse=True)
for i,(name,v) in enumerate(rank,1):v['weekly_rank']=i
arank=sorted(a_share.items(),key=lambda kv:kv[1].get('weekly_pct') if kv[1].get('weekly_pct') is not None else -999,reverse=True)
for i,(name,v) in enumerate(arank,1):v['weekly_rank']=i
boards,status=eastmoney_boards()
weekly_boards=[]
if boards:
    for b in boards:
        wp,week=board_weekly_pct(b['code'])
        if wp is not None:
            x=dict(b); x['weekly_pct']=wp; x['weekly_period']=week; weekly_boards.append(x)
        time.sleep(.08)
    weekly_boards.sort(key=lambda x:x['weekly_pct'],reverse=True)
positive=[x for x in weekly_boards if x['weekly_pct']>0]
negative=[x for x in reversed(weekly_boards) if x['weekly_pct']<0]
payload={'updated':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'method':'US sector ETF proxy + Eastmoney A-share industry board daily and weekly K-line ranking + A-share major index observations','sectors':us,'a_share':a_share,'a_share_industry_boards':boards,'a_share_board_status':status,'a_share_weekly_industry_boards':weekly_boards,'weekly_risers':[n for n,v in rank if (v.get('weekly_pct') or 0)>0],'weekly_fallers':[n for n,v in reversed(rank) if (v.get('weekly_pct') or 0)<0],'a_share_weekly_risers':positive[:10],'a_share_weekly_fallers':negative[:10],'a_share_board_risers':[x['name'] for x in boards[:5]],'a_share_board_fallers':[x['name'] for x in boards[-5:][::-1]]}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); print('market sectors:',len(us),'A-share indices:',len(a_share),'A-share industry boards:',len(boards),'weekly boards:',len(weekly_boards),'status:',status)
