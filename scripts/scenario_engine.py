import json, os, re, urllib.request, sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "scenario_state.json"
KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

def read(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return default

def parse_dt(v):
    if not v: return None
    try:
        return datetime.fromisoformat(str(v).replace(" UTC","+00:00").replace("Z","+00:00")).astimezone(timezone.utc)
    except Exception:
        return None

def latest_rows(rows, days=14):
    cut = datetime.now(timezone.utc) - timedelta(days=days)
    out=[]
    for n in rows:
        d=parse_dt(n.get("time") or n.get("updated") or n.get("published"))
        if d is None or d >= cut: out.append(n)
    return out

def pick_events(rows, limit=12):
    def score(n):
        s=float(n.get("ai_importance", n.get("importance_score", 0)) or 0)
        if n.get("official"): s += 15
        if n.get("risk") in ("极高","高") or n.get("ai_risk") in ("极高","高"): s += 15
        cat=n.get("ai_category") or n.get("cat") or ""
        if cat in ("中美博弈","国防","国家安全","贸易 / 供应链","能源 / 资源","金融","科技 / AI"): s += 8
        return s
    seen=set(); chosen=[]
    for n in sorted(latest_rows(rows), key=score, reverse=True):
        url=n.get("url") or ""
        title=n.get("titleZh") or n.get("title") or ""
        key=url or title
        if not key or key in seen: continue
        seen.add(key)
        chosen.append({
            "title": title[:220],
            "original_title": (n.get("title") or "")[:220],
            "region": n.get("ai_region") or n.get("region") or "global",
            "category": n.get("ai_category") or n.get("cat") or "全球政策",
            "risk": n.get("ai_risk") or n.get("risk") or "低",
            "importance": int(n.get("ai_importance", n.get("importance_score", 0)) or 0),
            "source": n.get("sourceOrg") or n.get("source") or "未知来源",
            "source_tier": n.get("sourceTier") or n.get("sourceType") or "",
            "url": url,
            "time": n.get("time") or n.get("updated") or ""
        })
        if len(chosen)>=limit: break
    return chosen

def market_state(d):
    m=d.get("market",[])
    wanted=("USD/CNY","上证指数","深证成指","沪深300","标普500","美国10年期收益率","布伦特原油","黄金","VIX")
    return [x for x in m if x.get("name") in wanted]

def top_sector(data, key, reverse=True, n=5):
    items=[]
    for name,x in (data.get(key) or {}).items():
        if isinstance(x,dict) and isinstance(x.get("weekly_pct"),(int,float)):
            items.append({"name":name,"weekly_pct":x["weekly_pct"],"monthly_pct":x.get("monthly_pct"),"ticker":x.get("ticker")})
    return sorted(items,key=lambda x:x["weekly_pct"],reverse=reverse)[:n]

def deterministic(news,dash,policy,ai):
    events=pick_events(news)
    cats=Counter(e["category"] for e in events); regs=Counter(e["region"] for e in events)
    pm=dash.get("policy_language",[])
    language={x.get("keyword"):x.get("count") for x in pm if isinstance(x,dict)}
    ms=dash.get("us_sector_market") or {}
    am=dash.get("a_share_market") or {}
    scenarios=[
      {"id":"base","name":"A · 基准路径","condition":"现有政策与已公布措施按当前节奏推进，没有出现新的重大升级或回撤。","chain":["现有政策执行","企业/政府响应","市场重新定价","供应链逐步消化","下一轮政策反馈"],"watch":["后续正式政策文本","执行细则与时间表","市场是否持续验证政策影响"]},
      {"id":"escalate","name":"B · 升级路径","condition":"出现新增制裁、关税、出口管制、军事行动或关键运输/能源供给扰动。","chain":["新增措施","对手或相关方反制","能源/贸易/金融成本上升","企业调整供应链","政策进一步反馈"],"watch":["新增强制性措施","能源/航运异常","关键资产波动与官方反制措辞"]},
      {"id":"ease","name":"C · 缓和路径","condition":"主要参与方出现可验证的沟通、豁免、延期、撤回或执行强度下降。","chain":["缓和信号","企业恢复/延后决策","风险溢价回落","贸易与供应链修复","后续政策确认"],"watch":["正式协议/豁免文本","措施实际撤回","市场与实体数据是否同步改善"]},
      {"id":"shock","name":"D · 外生冲击","condition":"出现当前资料未覆盖的重大突发事件，导致既有情景假设失效。","chain":["突发冲击","参与方紧急响应","市场与物流先行波动","政策工具箱扩张","重新建立情景树"],"watch":["异常市场波动","突发官方通告","能源/航运/支付系统异常"]}
    ]
    signals=[
      {"name":"政策强度","trigger":"新法令、行政命令、制裁、关税、出口管制或正式监管文本出现","why":"这是从讨论/表态进入可执行政策的关键节点"},
      {"name":"能源与运输","trigger":"原油、航运、关键通道或保险成本出现异常变化","why":"可把地缘事件传导到通胀、贸易和供应链"},
      {"name":"金融条件","trigger":"汇率、利率、信用或主要股指出现持续性异常","why":"验证市场是否开始定价二阶影响"},
      {"name":"供应链","trigger":"关键原材料、芯片、设备或物流出现供给限制","why":"验证政策是否进入实体经济"},
      {"name":"官方措辞","trigger":"主要参与方从一般表态转为明确期限、对象和执行措施","why":"提高情景切换的证据强度"}
    ]
    top_risks=[]
    for e in events[:8]:
        if e["risk"] in ("高","极高"): top_risks.append(e["title"])
    summary={
      "headline":"基于最新公开情报的全局情景底盘",
      "executive_summary":"系统将当前公开事实与模型推断分开。当前沙盘不把任何单一事件直接等同于未来结果，而是通过基准、升级、缓和和外生冲击四条路径观察条件变化。",
      "state":{
        "china":{"signal":"政策与经济数据持续更新","event_count":regs.get("china",0)},
        "us":{"signal":"政策、金融与地缘工具并行观察","event_count":regs.get("us",0)},
        "global":{"signal":"多地区事件与跨境传导需要联动观察","event_count":regs.get("global",0)},
        "finance":{"market":market_state(dash),"us_sector_risers":top_sector(ms,"us_sector_market",True),"us_sector_fallers":top_sector(ms,"us_sector_market",False),"a_share_risers":top_sector(am,"a_share_market",True),"a_share_fallers":top_sector(am,"a_share_market",False)},
        "policy_language":language
      },
      "events":events,
      "scenarios":scenarios,
      "signals":signals,
      "red_team":[
        "把媒体报道误当成政策事实：必须回到原始文件或明确来源。",
        "把相关性当因果关系：市场变化只能作为验证信号，不能单独证明政策效果。",
        "忽略参与方反应：每个升级情景都必须列出至少一个潜在反制或适应路径。",
        "时间尺度混淆：7天内信号与90天结构性变化分开。",
        "数据缺口：如果新闻、政策或金融数据不足，降低结论置信度而不是补写事实。"
      ],
      "action_framework":{
        "immediate":"只处理已确认、低成本、可逆的事项；记录事实与来源。",
        "watchlist":"围绕政策文本、市场条件、能源运输、供应链和官方措辞设置监控。",
        "backup":"为每条主要情景准备可逆的备用路径，不预设情景一定发生。",
        "stop":"出现关键假设被新证据推翻、数据源异常或重大外生冲击时重新推演。"
      },
      "evidence":{
        "confirmed":"新闻、政策、市场数据及其来源字段",
        "inference":"事件之间的影响链和情景分支",
        "assumption":"每条情景的触发条件",
        "unknown":"尚未被公开数据验证的动因、执行效果和后续反应"
      },
      "data_health":{
        "dashboard_updated":dash.get("updated"),
        "policy_updated":policy.get("updated"),
        "news_count":len(news),
        "ai_available":bool(ai)
      },
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "engine":"scenario-engine-v2-deterministic"
    }
    return summary

def call_ai(base):
    if not KEY: return None
    prompt="""你是战略情报沙盘的校验层。只能使用输入JSON中的事实和来源，不得引入未提供的现实事件。输出合法JSON，保留events原样。可以改写headline、executive_summary、scenarios、signals、red_team、action_framework，但所有判断必须标记为推断/假设；不得给出政治人物、政党或政策的支持/反对评价，不得做选举预测，不得伪造概率。不要提供个股买卖建议。输出完整对象。输入："""+json.dumps(base,ensure_ascii=False)
    body={"model":MODEL,"messages":[{"role":"system","content":"你是中立的全球政策情景分析校验器。"},{"role":"user","content":prompt}],"stream":False,"max_tokens":6000,"response_format":{"type":"json_object"}}
    req=urllib.request.Request("https://api.deepseek.com/chat/completions",data=json.dumps(body,ensure_ascii=False).encode(),headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json","User-Agent":"China-US-Global-Intelligence-Radar/Scenario-2.0"})
    try:
        raw=urllib.request.urlopen(req,timeout=120).read().decode("utf-8")
        return json.loads(json.loads(raw)["choices"][0]["message"]["content"])
    except Exception as e:
        print("Scenario AI error:",type(e).__name__)
        return None

def main():
    news=read("news.json",[])
    dash=read("dashboard.json",{})
    policy=read("policy_radar.json",{})
    ai=read("ai_summaries.json",{})
    base=deterministic(news,dash,policy,ai)
    enhanced=call_ai(base)
    if isinstance(enhanced,dict):
        enhanced["events"]=base["events"]
        enhanced["data_health"]=base["data_health"]
        enhanced["generated_at"]=datetime.now(timezone.utc).isoformat()
        enhanced["engine"]="scenario-engine-v2-ai-validated"
        state=enhanced
    else:
        state=base
    OUT.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Scenario state generated:",state["engine"],"events=",len(state.get("events",[])))
    return 0

if __name__=="__main__": sys.exit(main())
