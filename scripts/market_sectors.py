import json, urllib.request, time
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'market_sectors.json'
# Transparent market observations. US sectors use SPDR sector ETFs; A-share uses major index proxies.
SECTORS={'科技':'XLK','金融':'XLF','能源':'XLE','工业':'XLI','可选消费':'XLY','必选消费':'XLP','医疗':'XLV','材料':'XLB','房地产':'XLRE','通信服务':'XLC','公用事业':'XLU'}
A_SHARE={'上证指数':'000001.SS','深证成指':'399001.SZ','沪深300':'000300.SS','中证500':'000905.SS','中证1000':'000852.SS','创业板指':'399006.SZ','科创50':'000688.SS'}
UA='China-US-Global-Intelligence-Radar/Market-Collector-2.0'
def get(ticker):
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=6mo&interval=1d'
    try:
        req=urllib.request.Request(url,headers={'User-Agent':UA}); obj=json.loads(urllib.request.urlopen(req,timeout=15).read().decode())
        r=obj['chart']['result'][0]; q=r['indicators']['quote'][0]; closes=[x for x in q['close'] if x is not None]; ts=[x for x,c in zip(r['timestamp'],q['close']) if c is not None]
        if len(closes)<2:return None
        now=closes[-1]
        def ret(days):
            if len(closes)<=days:return None
            return round((now/closes[-days-1]-1)*100,2)
        return {'ticker':ticker,'latest':round(now,4),'daily_pct':ret(1),'weekly_pct':ret(5),'monthly_pct':ret(21),'quarterly_pct':ret(63),'six_month_pct':round((now/closes[0]-1)*100,2),'asof':datetime.fromtimestamp(ts[-1],timezone.utc).strftime('%Y-%m-%d')}
    except Exception:return None
us={};
for name,t in SECTORS.items():
    v=get(t)
    if v:us[name]=v
    time.sleep(.12)
a_share={}
for name,t in A_SHARE.items():
    v=get(t)
    if v:a_share[name]=v
    time.sleep(.12)
rank=sorted(us.items(),key=lambda kv:kv[1].get('weekly_pct') if kv[1].get('weekly_pct') is not None else -999,reverse=True)
for i,(name,v) in enumerate(rank,1):v['weekly_rank']=i
arank=sorted(a_share.items(),key=lambda kv:kv[1].get('weekly_pct') if kv[1].get('weekly_pct') is not None else -999,reverse=True)
for i,(name,v) in enumerate(arank,1):v['weekly_rank']=i
payload={'updated':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'method':'US sector ETF proxy + A-share major index observations; returns are market observations, not investment advice','sectors':us,'a_share':a_share,'weekly_risers':[n for n,v in rank if (v.get('weekly_pct') or 0)>0],'weekly_fallers':[n for n,v in reversed(rank) if (v.get('weekly_pct') or 0)<0],'a_share_weekly_risers':[n for n,v in arank if (v.get('weekly_pct') or 0)>0],'a_share_weekly_fallers':[n for n,v in reversed(arank) if (v.get('weekly_pct') or 0)<0]}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); print('market sectors:',len(us),'A-share indices:',len(a_share))
