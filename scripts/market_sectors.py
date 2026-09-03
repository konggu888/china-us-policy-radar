import json, urllib.request, time
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'market_sectors.json'
# Sector ETFs are transparent proxies for broad US sector performance.
SECTORS={'科技':'XLK','金融':'XLF','能源':'XLE','工业':'XLI','可选消费':'XLY','必选消费':'XLP','医疗':'XLV','材料':'XLB','房地产':'XLRE','通信服务':'XLC','公用事业':'XLU'}
UA='China-US-Global-Intelligence-Radar/Market-Collector-1.0'
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
        return {'ticker':ticker,'latest':now,'daily_pct':ret(1),'weekly_pct':ret(5),'monthly_pct':ret(21),'quarterly_pct':ret(63),'six_month_pct':round((now/closes[0]-1)*100,2),'asof':datetime.fromtimestamp(ts[-1],timezone.utc).strftime('%Y-%m-%d')}
    except Exception:return None
out={}
for name,t in SECTORS.items():
    v=get(t)
    if v:out[name]=v
    time.sleep(.15)
rank=sorted(out.items(),key=lambda kv:kv[1].get('weekly_pct') if kv[1].get('weekly_pct') is not None else -999,reverse=True)
for i,(name,v) in enumerate(rank,1):v['weekly_rank']=i
payload={'updated':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'method':'US sector ETF proxy; returns are market observations, not investment advice','sectors':out,'weekly_risers':[n for n,v in rank if (v.get('weekly_pct') or 0)>0],'weekly_fallers':[n for n,v in reversed(rank) if (v.get('weekly_pct') or 0)<0]}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); print('market sectors:',len(out))
