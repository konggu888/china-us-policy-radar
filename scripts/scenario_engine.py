import json,os,urllib.request,sys,re
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'scenario_state.json'
MARKET_SNAPSHOTS=DATA/'market_snapshots.json'
KEY=os.getenv('DEEPSEEK_API_KEY','').strip(); MODEL=os.getenv('DEEPSEEK_MODEL','deepseek-v4-flash')
def read(n,d):
 try:return json.loads((DATA/n).read_text(encoding='utf-8'))
 except Exception:return d
def dt(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
 except:return None
def recent(rows,days=14):
 cut=datetime.now(timezone.utc)-timedelta(days=days)
 return [x for x in rows if not dt(x.get('time') or x.get('updated') or x.get('published')) or dt(x.get('time') or x.get('updated') or x.get('published'))>=cut]
def events(rows,limit=15):
 def score(x):
  s=float(x.get('ai_importance',x.get('importance_score',0)) or 0)+(15 if x.get('official') else 0)
  s+=15 if x.get('risk') in ('高','极高') or x.get('ai_risk') in ('高','极高') else 0
  return s
 out=[];seen=set()
 for n in sorted(recent(rows),key=score,reverse=True):
  u=n.get('url',''); t=n.get('titleZh') or n.get('title') or ''; k=u or t
  if not k or k in seen:continue
  seen.add(k);out.append({'title':t[:220],'region':n.get('ai_region') or n.get('region') or 'global','category':n.get('ai_category') or n.get('cat') or '全球政策','risk':n.get('ai_risk') or n.get('risk') or '低','source':n.get('sourceOrg') or n.get('source') or '未知来源','url':u,'time':n.get('time') or n.get('updated') or ''})
  if len(out)>=limit:break
 return out
def markets(d):
 m=d.get('market',[])
 wanted=('USD/CNY','上证指数','深证成指','沪深300','标普500','美国10年期收益率','布伦特原油','黄金','VIX')
 return [x for x in m if x.get('name') in wanted]
def sectors(d,key,rev=True):
 a=[]
 for n,x in (d.get(key) or {}).items():
  if isinstance(x,dict) and isinstance(x.get('weekly_pct'),(int,float)):a.append({'name':n,'weekly_pct':x['weekly_pct']})
 return sorted(a,key=lambda z:z['weekly_pct'],reverse=rev)[:5]
def layer_state(news,dash,social):
 es=events(news); cats=Counter(x['category'] for x in es); regs=Counter(x['region'] for x in es); sc=social.get('theme_counts',{})
 # 10 layers: evidence-backed observations first; no claim that discussion proxy equals public opinion.
 return [
  {'id':'policy','name':'政策','signal':f'近14日重点事件 {len(es)} 条；政策类 {sum(v for k,v in cats.items() if "政策" in k or "政治" in k or "内政" in k)} 条','evidence':'news/policy_radar'},
  {'id':'public','name':'民众体感','signal':f'公开讨论代理信号：就业/收入 {sc.get("就业/收入",0)}、住房 {sc.get("住房/房价",0)}、物价 {sc.get("物价/生活成本",0)}、消费 {sc.get("消费",0)}','evidence':'social_signals','caveat':'仅代表公开讨论发现，不代表总体民意或民调'},
  {'id':'enterprise','name':'企业层','signal':'从产业、就业、贸易、融资与投资相关新闻建立企业行为观察；当前缺少统一企业调查样本','evidence':'news','caveat':'暂无代表性企业调查时不做强结论'},
  {'id':'finance','name':'金融市场','signal':f'可用市场变量 {len(markets(dash))} 项；观察股/债/汇/商品联动','evidence':'dashboard'},
  {'id':'capital','name':'资金流向','signal':'跟踪汇率、利率、股债商品与行业相对表现；暂不把单一价格变化解释成资金迁徙','evidence':'dashboard','caveat':'需要连续资金流数据才能确认迁徙方向'},
  {'id':'supply','name':'产业链','signal':'重点观察贸易、航运、能源、芯片、关键原材料及行业表现','evidence':'news/market_sectors'},
  {'id':'international','name':'国际反馈','signal':f'中国/美国/全球重点事件 {regs.get("china",0)}/{regs.get("us",0)}/{regs.get("global",0)}','evidence':'news/policy_radar'},
  {'id':'execution','name':'政策执行','signal':'区分政策发布、部署、执行细则与实体效果；当前页面只把公开文本作为执行证据','evidence':'policy_radar','caveat':'未观察到执行证据时保持未知'},
  {'id':'unknown','name':'未知区域','signal':'主动记录数据缺口、来源冲突、样本偏差和尚未验证的机制','evidence':'model'},
  {'id':'falsification','name':'反证机制','signal':'每条情景同时列出可能推翻它的观察信号，数据变化后重新计算','evidence':'model'}
 ]
def governance_layer(news):
 rows=[]
 pats=[r'反腐|落马|被查|接受审查|纪律审查|监察调查|违纪违法|开除党籍|逮捕|起诉|中央纪委|纪委监委',r'任职|履历|书记|省长|部长|副部长|市长|市委|省委|董事长|党委']
 for n in recent(news,90):
  t=n.get('titleZh') or n.get('title') or ''
  if re.search(pats[0],t,re.I):
   rows.append({'title':t[:220],'source':n.get('sourceOrg') or n.get('source') or '未知来源','url':n.get('url',''),'time':n.get('time') or n.get('updated') or '','region':n.get('ai_region') or n.get('region') or 'global','person_or_entity':n.get('person') or n.get('name') or '待核实','role_or_place':n.get('role') or n.get('location') or '待核实'})
 return rows[:30]

HORIZONS = [
    ("T1D","超短期 1天",0,1),
    ("T7D","短期 1周",1,7),
    ("T15D","短期 15天",7,15),
    ("T30D","中短期 30天",15,30),
    ("T180D","中长期 6个月",30,180),
    ("T365D","长期 1年",180,365),
]

def _country_for_region(region):
    r=str(region or "").lower()
    if r in ("china","cn","中国"): return "CN"
    if r in ("us","usa","美国"): return "US"
    if r in ("eu","europe","欧盟"): return "EU"
    if r in ("jp","japan","日本"): return "JP"
    if r in ("kr","korea","韩国"): return "KR"
    if r in ("in","india","印度"): return "IN"
    if r in ("ru","russia","俄罗斯"): return "RU"
    if r in ("gb","uk","英国"): return "GB"
    if r in ("au","australia","澳大利亚"): return "AU"
    if r in ("me","middle_east","中东"): return "ME"
    return "OTHER"

def _norm_title(v):
    s=re.sub(r"\s+"," ",str(v or "").lower()).strip()
    return re.sub(r"[^0-9a-z\\u4e00-\\u9fff]+","",s)

def _source_meta(n):
    src=str(n.get("sourceOrg") or n.get("source") or "未知来源")
    official=bool(n.get("official")) or bool(re.search(r"政府|国务院|外交部|商务部|财政部|央行|白宫|state\\.gov|treasury|commerce|europa",src,re.I))
    tier="PRIMARY" if official else ("KNOWN_MEDIA" if src!="未知来源" else "UNKNOWN")
    return src,tier,(0.95 if tier=="PRIMARY" else (0.75 if tier=="KNOWN_MEDIA" else 0.45))

def _is_duplicate_title(norm,seen_norms):
    if not norm:return True
    for old in seen_norms:
        if norm==old:return True
        if len(norm)>=16 and len(old)>=16:
            overlap=len(set(norm)&set(old))/max(1,len(set(norm)|set(old)))
            if overlap>=0.88:return True
    return False

def _event_fingerprint(n):
    """Stable event identity: normalized title plus category/region, avoiding URL-only identity."""
    title=_norm_title(n.get("titleZh") or n.get("title") or "")
    cat=_norm_title(n.get("category") or n.get("cat") or "全球政策")
    region=_norm_title(n.get("region") or n.get("ai_region") or "global")
    return "|".join(x for x in (title,cat,region) if x)

def _source_identity(n):
    src=str(n.get("sourceOrg") or n.get("source") or "未知来源").strip().lower()
    url=str(n.get("url") or "").strip().lower()
    host=re.sub(r"^https?://","",url).split("/")[0]
    return src or host or "未知来源"

def _corroboration(events):
    """Count independent sources without letting repost volume multiply one event."""
    by={}
    for e in events:
        k=e.get("dedupeKey") or e.get("id")
        if not k: continue
        by.setdefault(k,{"sources":set(),"tiers":set(),"count":0})
        s=e.get("source",{})
        by[k]["sources"].add(s.get("provider") or "未知来源")
        by[k]["tiers"].add(s.get("tier") or "UNKNOWN")
        by[k]["count"]+=1
    return by

def _event_lifecycle(age,status,tier):
    if status=="RESOLVED": return "RESOLVED"
    if status=="DEVELOPING": return "DEVELOPING"
    if age is None: return "UNVERIFIED_TIME"
    if age<=1: return "NEW"
    if age<=7: return "ACTIVE"
    if age<=30: return "WATCH"
    return "DECAYED"

def _evidence_weight(age,cred,tier):
    freshness=1.0 if age is None else (1.0 if age<=1 else (0.85 if age<=7 else (0.55 if age<=30 else 0.25)))
    return round(max(0.05,min(1.0,cred*freshness)),3)

def build_global_events(rows,limit=20):
    out=[]; seen=set(); seen_norms=[]; now=datetime.now(timezone.utc).isoformat()
    for n in events(rows,limit=limit):
        region=n.get("region") or "global"; cc=_country_for_region(region)
        norm=_event_fingerprint(n)
        if _is_duplicate_title(norm,seen_norms):continue
        seen_norms.append(norm)
        # Third-party events are first-class triggers, not discarded as unrelated noise.
        role="CATALYST" if cc not in ("CN","US") else "BACKGROUND"
        if not out: role="PRIMARY_TRIGGER"
        cat=str(n.get("category") or "全球政策")
        cmap={"贸易 / 供应链":"TRADE","能源 / 资源":"ENERGY","科技 / AI":"TECHNOLOGY","金融":"FINANCE","中美博弈":"GEOPOLITICS","全球政策":"POLITICS","国防":"SECURITY","外交":"GEOPOLITICS"}
        ec=cmap.get(cat,cat.upper().replace(" ","_").replace("/","_"))
        importance="CRITICAL" if n.get("risk")=="极高" else ("HIGH" if n.get("risk")=="高" else "MEDIUM")
        channels=[]
        if "TRADE" in ec or "TARIFF" in ec: channels.append({"id":f"{n.get('url','event')}-trade","name":"TRADE","intensity":0.65,"description":"贸易成本与市场准入传导"})
        if "ENERGY" in ec or "LOGISTICS" in ec: channels.append({"id":f"{n.get('url','event')}-energy","name":"ENERGY","intensity":0.60,"description":"能源/运输成本传导"})
        if not channels: channels.append({"id":f"{n.get('url','event')}-supply","name":"SUPPLY_CHAIN","intensity":0.45,"description":"供应链与产业传导"})
        src,tier,cred=_source_meta(n)
        published=n.get("time") or n.get("updated") or n.get("published") or ""
        pdt=dt(published); age=(datetime.now(timezone.utc)-pdt).total_seconds()/86400 if pdt else None
        freshness="NEW" if age is not None and age<=1 else ("RECENT" if age is not None and age<=7 else ("STALE" if age is not None else "UNKNOWN"))
        out.append({
            "id":"evt-"+str(len(out)+1),
            "title":n.get("title",""),
            "summary":n.get("title",""),
            "category":ec,
            "importance":importance,
            "actor":{"type":"COUNTRY" if cc not in ("EU","ME","OTHER") else "REGION","country":cc,"name":region},
            "affectedCountries":[cc] if cc!="OTHER" else ["CN","US"],
            "source":{"provider":src,"url":n.get("url",""),"publishedAt":published,"fetchedAt":now,"credibility":cred,"tier":tier,"ageDays":round(age,2) if age is not None else None,"freshness":freshness,"lifecycle":_event_lifecycle(age,n.get("status","CONFIRMED"),tier),"evidenceWeight":_evidence_weight(age,cred,tier)},
            "status":n.get("status") if n.get("status") in ("RUMOR","DEVELOPING","CONFIRMED","RESOLVED") else "CONFIRMED",
            "triggerRole":role,
            "impact":{"china":0,"us":0,"globalTrade":0,"logistics":0,"finance":0,"energy":0,"technology":0},
            "channels":channels,
            "tags":[str(region),ec],"dedupeKey":norm,"sourceIdentity":_source_identity(n)
        })
    corr=_corroboration(out)
    for e in out:
        c=corr.get(e.get("dedupeKey"),{"sources":set(),"tiers":set(),"count":1})
        independent=len(c["sources"])
        source_bonus=min(0.25,0.08*max(0,independent-1))
        e["corroboration"]={"independentSourceCount":independent,"reportCount":c["count"],"tierCount":len(c["tiers"]),"sources":sorted(c["sources"])}
        e["source"]["corroborationBonus"]=round(source_bonus,3)
        e["source"]["evidenceWeight"]=round(min(1.0,float(e["source"].get("evidenceWeight",0))+source_bonus),3)
    return out[:limit]

def _action_matrix(prefix, horizon):
    h=horizon[0]
    return {
      "investment":{"domain":"INVESTMENT","do":[
        {"id":f"{prefix}-inv-do-{h}","polarity":"DO","title":"复核汇率与流动性敞口","action":"按本时间窗口重新核算 USD/CNY、现金及外币收支的敏感度，并保留足够流动性。","rationale":"政策与外部冲击可能先通过汇率和流动性传导。","urgency":"HIGH" if h in ("T1D","T7D") else "MEDIUM","relatedSignals":["USD/CNY","liquidity"]}
      ],"dont":[
        {"id":f"{prefix}-inv-dont-{h}","polarity":"DONT","title":"不要因单一事件集中调整资产","action":"不把单一新闻直接转换为大额、不可逆的资产配置动作。","rationale":"情景存在分支且短期价格变化不能单独证明长期路径。","urgency":"MEDIUM"}
      ],"watch":[
        {"id":f"{prefix}-inv-watch-{h}","polarity":"WATCH","title":"观察避险与风险资产联动","action":"跟踪黄金、美债、股票、美元及加密资产的同步/背离变化。","rationale":"用于识别风险偏好变化，而非单独作为资金迁徙证明。","urgency":"MEDIUM"}
      ]},
      "trade":{"domain":"TRADE","do":[
        {"id":f"{prefix}-trade-do-{h}","polarity":"DO","title":"核算关税与物流成本","action":"更新关税、保险、运费、交付周期和库存安全边际。","rationale":"第三方事件可通过供应链和航运成为中美博弈的催化剂。","urgency":"HIGH" if h in ("T1D","T7D","T15D") else "MEDIUM","relatedSignals":["tariff","shipping","lead_time"]}
      ],"dont":[
        {"id":f"{prefix}-trade-dont-{h}","polarity":"DONT","title":"不要未经合规审查进行转口","action":"不得把第三方转口作为规避关税、出口管制或制裁的默认方案；先核验原产地、海关与制裁规则。","rationale":"第三方路线可能增加合规、成本和追溯风险。","urgency":"HIGH"}
      ],"watch":[
        {"id":f"{prefix}-trade-watch-{h}","polarity":"WATCH","title":"监控支付与资金通道","action":"检查银行、Wise、SEPA、离岸账户及收付款对手方的可用性和合规要求。","rationale":"支付通道是跨境贸易链的重要节点。","urgency":"MEDIUM"}
      ]},
      "life":{"domain":"LIFE","do":[
        {"id":f"{prefix}-life-do-{h}","polarity":"DO","title":"建立现金流预警线","action":"按未来本时间窗口的固定支出、收入和跨境支付依赖设置预警线。","rationale":"外部冲击可能造成收入或支付延迟。","urgency":"HIGH" if h in ("T1D","T7D") else "MEDIUM"}
      ],"dont":[
        {"id":f"{prefix}-life-dont-{h}","polarity":"DONT","title":"不要把全部生活资金放在单一通道","action":"避免单一银行、单一支付渠道或单一司法辖区形成关键依赖。","rationale":"降低单点故障风险。","urgency":"MEDIUM"}
      ],"watch":[
        {"id":f"{prefix}-life-watch-{h}","polarity":"WATCH","title":"关注资产隔离与身份/出行政策","action":"按所在司法辖区检查海外资产、身份文件、保险、签证及航线变化。","rationale":"长期跨境风险不仅来自金融，也来自司法与出行规则变化。","urgency":"MEDIUM"}
      ]}
    }

def _scenario_horizons(prefix, scenario_type):
    out=[]
    for h in HORIZONS:
        matrix=_action_matrix(prefix,h)
        if scenario_type=="HARD_DECOUPLING":
            impacts=[{"domain":"INVESTMENT","direction":"MIXED","intensity":0.75,"explanation":"风险溢价和汇率敏感度上升。"},{"domain":"TRADE","direction":"NEGATIVE","intensity":0.85,"explanation":"关税、物流和供应链重构压力增加。"},{"domain":"LIFE","direction":"MIXED","intensity":0.45,"explanation":"现金流、支付和出行依赖需要更多冗余。"}]
        elif scenario_type=="STRUCTURAL_NEGOTIATION":
            impacts=[{"domain":"INVESTMENT","direction":"MIXED","intensity":0.40,"explanation":"不确定性下降但结构性竞争仍在。"},{"domain":"TRADE","direction":"MIXED","intensity":0.45,"explanation":"局部措施可能维持，企业重新定价成本。"},{"domain":"LIFE","direction":"POSITIVE","intensity":0.25,"explanation":"跨境通道压力可能相对稳定。"}]
        else:
            impacts=[{"domain":"INVESTMENT","direction":"MIXED","intensity":0.55,"explanation":"区域资产与汇率分化可能扩大。"},{"domain":"TRADE","direction":"MIXED","intensity":0.65,"explanation":"第三方路线增加但合规和物流成本同步上升。"},{"domain":"LIFE","direction":"MIXED","intensity":0.35,"explanation":"司法辖区、支付和出行差异更重要。"}]
        signals=[
          {"id":f"{prefix}-sig-{h}-fx","name":"USD/CNY","metric":"汇率与波动","direction":"VOLATILE","importance":"HIGH"},
          {"id":f"{prefix}-sig-{h}-trade","name":"贸易/航运成本","metric":"关税、运费、交付周期","direction":"UP" if scenario_type!="STRUCTURAL_NEGOTIATION" else "STABLE","importance":"HIGH"}
        ]
        out.append({"horizon":h,"label":h[1],"startOffsetDays":h[2],"endOffsetDays":h[3],"keySignals":signals,"impacts":impacts,"actions":matrix})
    return out

def _calibration_audit(trigger_calibration):
    rows=[]
    for x in trigger_calibration or []:
        if x.get("status")!="CALIBRATED": continue
        factor=float(x.get("calibrationWeight",1.0) or 1.0)
        rows.append({
            "trigger":x.get("trigger"),
            "sampleSize":x.get("observations",0),
            "historicalSignalRate":x.get("historicalSignalRate"),
            "baseFactor":1.0,
            "appliedFactor":factor,
            "delta":round(factor-1.0,3),
            "direction":"UP" if factor>1 else ("DOWN" if factor<1 else "UNCHANGED"),
            "reason":"基于历史样本中的明显市场偏离占比；仅调整监测敏感度。",
            "guardrail":"bounded_0.8_1.2"
        })
    return rows

def _calibration_guard(trigger_calibration, previous_audit=None):
    """Freeze suspicious calibration changes and retain a rollback snapshot."""
    prev={str(x.get("trigger")):x for x in (previous_audit or [])}
    guarded=[]; audit=[]
    for x in trigger_calibration or []:
        trigger=str(x.get("trigger") or "UNKNOWN_TRIGGER")
        factor=float(x.get("calibrationWeight",1.0) or 1.0)
        samples=int(x.get("observations",0) or 0)
        old=prev.get(trigger)
        prior=float(old.get("appliedFactor",1.0)) if old else 1.0
        reasons=[]
        if samples<3: reasons.append("SAMPLE_TOO_SMALL")
        if abs(factor-prior)>0.20: reasons.append("LARGE_JUMP")
        applied=prior if reasons and old else factor
        status="FROZEN" if reasons and old else "APPLIED"
        guarded.append(dict(x,calibrationWeight=round(max(0.8,min(1.2,applied)),3),calibrationStatus=status))
        audit.append({"trigger":trigger,"sampleSize":samples,"previousFactor":prior,"proposedFactor":round(factor,3),"appliedFactor":round(applied,3),"status":status,"reasons":reasons,"rollbackAvailable":bool(old)})
    return guarded,audit

def _calibration_factor(trigger_calibration, trigger):
    row=next((x for x in (trigger_calibration or []) if x.get("trigger")==trigger and x.get("status")=="CALIBRATED"),None)
    if not row:return 1.0
    rate=row.get("historicalSignalRate")
    return round(max(0.8,min(1.2,0.8+0.4*float(rate))),3) if rate is not None else 1.0

def _scenario_activation(events, scenario_type, trigger_calibration=None):
    """Evidence-weighted activation state. This is a monitoring weight, not a probability forecast."""
    cats=[str(e.get("category","")).upper() for e in events]
    roles=[str(e.get("triggerRole","")) for e in events]
    confirmed=sum(float(e.get("source",{}).get("evidenceWeight",1.0) or 0) for e in events if e.get("status")=="CONFIRMED")
    third_party=sum(float(e.get("source",{}).get("evidenceWeight",1.0) or 0) for e in events if e.get("actor",{}).get("country") not in ("CN","US","OTHER",None))
    trade=sum(float(e.get("source",{}).get("evidenceWeight",1.0) or 0) for e in events if str(e.get("category","")).upper() in ("TRADE","TARIFF","SANCTIONS","TECHNOLOGY","PAYMENT"))
    shock=sum(float(e.get("source",{}).get("evidenceWeight",1.0) or 0) for e in events if str(e.get("category","")).upper() in ("GEOPOLITICS","ENERGY","PORT","LOGISTICS","CRITICAL_MINERALS"))
    trigger_names=[str(e.get("category") or e.get("triggerRole") or "UNKNOWN_TRIGGER") for e in events]
    factors=[_calibration_factor(trigger_calibration,x) for x in trigger_names]
    calibration=sum(factors)/len(factors) if factors else 1.0
    if scenario_type=="HARD_DECOUPLING":
        score=min(1.0,(0.12*confirmed+0.10*trade+0.08*shock)*calibration)
        evidence=["确认事件数量="+str(confirmed)]
        if trade:evidence.append("贸易/技术/制裁类信号="+str(trade))
        counter=["若出现明确豁免、延期或执行强度下降，应降低该路径权重"]
    elif scenario_type=="STRUCTURAL_NEGOTIATION":
        score=min(1.0,(0.10*confirmed+0.05*len([x for x in roles if x=="PRIMARY_TRIGGER"]))*calibration)
        evidence=["已有确认事件="+str(confirmed),"需要额外的官方缓和/豁免证据"]
        counter=["若出现新增强制措施并持续执行，应降低该路径权重"]
    else:
        score=min(1.0,(0.10*confirmed+0.12*third_party+0.08*shock)*calibration)
        evidence=["第三方事件="+str(third_party),"物流/能源/地缘信号="+str(shock)]
        counter=["若主要冲击完全停留在中美双边渠道，应降低该路径权重"]
    return {"activationState":"WATCH" if score<0.35 else ("ACTIVE" if score<0.70 else "ELEVATED"),"triggerScore":round(score,2),"evidence":evidence,"counterSignals":counter}

def _counter_signal_analysis(events, scenario_type):
    """Identify observable counter-signals separately from hypothetical counter-conditions."""
    rules={
        "HARD_DECOUPLING":{"opposite":{"POLITICS","DIPLOMACY"},"keywords":["豁免","延期","撤回","暂停执行","waiver","extension","suspend"]},
        "STRUCTURAL_NEGOTIATION":{"opposite":{"SANCTIONS","TARIFF","TRADE","TECHNOLOGY","PAYMENT"},"keywords":["新增制裁","加征关税","出口管制","investment restriction","export control"]},
        "THIRD_PARTY_DIVERSION":{"opposite":{"TRADE","TARIFF","SANCTIONS","TECHNOLOGY"},"keywords":["双边直接","直接贸易","直接供应","direct bilateral"]}
    }
    rule=rules.get(scenario_type,{"opposite":set(),"keywords":[]})
    rows=[]
    for e in events or []:
        cat=str(e.get("category","")).upper()
        title=str(e.get("title",""))
        if cat not in rule["opposite"] and not any(k.lower() in title.lower() for k in rule["keywords"]):
            continue
        ew=float(e.get("source",{}).get("evidenceWeight",0) or 0)
        rows.append({
            "eventId":e.get("id"),
            "title":title,
            "category":cat,
            "evidenceWeight":round(ew,3),
            "publishedAt":e.get("source",{}).get("publishedAt"),
            "tier":e.get("source",{}).get("tier"),
            "lifecycle":e.get("source",{}).get("lifecycle"),
            "interpretation":"候选反证；只有在事件内容与当前情景核心假设直接冲突时才应降低该路径监测权重。"
        })
    strength=round(sum(x["evidenceWeight"] for x in rows),3)
    return {
        "status":"OBSERVED_COUNTER_SIGNAL" if rows else "NO_OBSERVED_COUNTER_SIGNAL",
        "count":len(rows),
        "strength":strength,
        "signals":rows[:8],
        "rule":"反证是监测信号，不等于情景被证伪；需要时间、来源和执行证据进一步确认。"
    }

def _merge_evidence_registry(current_events, previous_snapshot):
    old={str(x.get("dedupeKey")):x for x in (previous_snapshot or {}).get("evidenceRegistry",[]) if x.get("dedupeKey")}
    now=datetime.now(timezone.utc).isoformat()
    registry=[]
    for e in current_events:
        k=e.get("dedupeKey")
        if not k: continue
        s=e.get("source",{}); prev=old.get(k,{})
        sources=set(prev.get("sourceIds",[]) or [])
        sources.add(str(e.get("sourceIdentity") or s.get("provider") or "UNKNOWN"))
        registry.append({"dedupeKey":k,"title":e.get("title"),"firstSeenAt":prev.get("firstSeenAt") or s.get("publishedAt") or now,"lastSeenAt":now,"observationCount":int(prev.get("observationCount",0) or 0)+1,"sourceIds":sorted(sources),"independentSourceCount":len(sources),"lifecycle":s.get("lifecycle","UNVERIFIED_TIME"),"freshness":s.get("freshness","UNKNOWN"),"evidenceWeight":s.get("evidenceWeight",0),"tier":s.get("tier","UNKNOWN")})
    return registry

def _evidence_lifecycle(age_days, status, tier, observation_count=1, independent_sources=1, has_followup=False):
    """Descriptive evidence aging state; does not assert truth/falsity."""
    s=str(status or "CONFIRMED").upper()
    age=float(age_days) if age_days is not None else None
    if s=="RESOLVED": return "EXPIRED"
    if s=="RUMOR": return "UNVERIFIED"
    if age is None: return "UNVERIFIED_TIME"
    if age <= 1: return "NEW"
    if age <= 7: return "SUSTAINED" if has_followup or independent_sources>=2 else "RECENT"
    if age <= 30: return "PENDING_CONFIRMATION" if not has_followup else "SUSTAINED"
    if age <= 90: return "DECAYING" if not has_followup else "SUSTAINED"
    if age <= 365: return "DECAYING" if not has_followup else "LONG_RUNNING"
    return "EXPIRED"

def build_evidence_graph(events, scenarios, lifecycle_rows=None):
    """Build an auditable evidence graph linking events, corroboration, follow-up and scenarios."""
    life={str(x.get("dedupeKey")):x for x in (lifecycle_rows or []) if x.get("dedupeKey")}
    nodes=[]; edges=[]; seen=set()
    def add_node(nid,kind,label,meta=None):
        if nid in seen:return
        seen.add(nid); nodes.append({"id":nid,"kind":kind,"label":label,"meta":meta or {}})
    for e in events or []:
        eid="event:"+str(e.get("dedupeKey") or e.get("id"))
        s=e.get("source",{}) or {}; add_node(eid,"EVENT",e.get("title",""),{"publishedAt":s.get("publishedAt"),"provider":s.get("provider"),"tier":s.get("tier")})
        l=life.get(str(e.get("dedupeKey")))
        if l:
            lid="lifecycle:"+str(e.get("dedupeKey")); add_node(lid,"LIFECYCLE",l.get("lifecycle",""),{"agingFactor":l.get("agingFactor"),"effectiveEvidenceWeight":l.get("effectiveEvidenceWeight")}); edges.append({"from":eid,"to":lid,"relation":"HAS_LIFECYCLE"})
        for sid in (e.get("corroboration",{}) or {}).get("sources",[]) or []:
            nid="source:"+str(sid); add_node(nid,"SOURCE",str(sid)); edges.append({"from":nid,"to":eid,"relation":"CORROBORATES"})
    for s in scenarios or []:
        sid="scenario:"+str(s.get("code") or s.get("id")); add_node(sid,"SCENARIO",s.get("code",""))
        for d in s.get("evidenceDrivers",[]) or []:
            if d.get("kind")!="EVENT":continue
            eid="event:"+str(d.get("dedupeKey") or d.get("id"))
            add_node(eid,"EVENT",d.get("title","")); edges.append({"from":eid,"to":sid,"relation":"SUPPORTS_MONITORING"})
        for x in s.get("counterSignalAnalysis",{}).get("signals",[]) or []:
            eid="event:"+str(x.get("eventId") or x.get("title")); add_node(eid,"EVENT",x.get("title","")); edges.append({"from":eid,"to":sid,"relation":"COUNTER_SIGNAL"})
    return {"generatedAt":datetime.now(timezone.utc).isoformat(),"nodes":nodes[:300],"edges":edges[:600],"interpretation":"图谱用于追踪证据来源、生命周期与情景关联；关系是监测关系，不表示因果或概率。"}

def build_evidence_lifecycle(events, previous_snapshot=None):
    """Reclassify evidence by age and observable follow-up/corroboration."""
    old={str(x.get("dedupeKey")):x for x in (previous_snapshot or {}).get("evidenceRegistry",[]) if x.get("dedupeKey")}
    now=datetime.now(timezone.utc)
    rows=[]
    for e in events or []:
        s=e.get("source",{}) or {}
        pub=dt(s.get("publishedAt"))
        age=(now-pub).total_seconds()/86400 if pub else None
        prev=old.get(str(e.get("dedupeKey")),{})
        sources=max(int(prev.get("independentSourceCount",0) or 0),int((e.get("corroboration") or {}).get("independentSourceCount",1) or 1))
        # A repeated observation or a second independent source is observable follow-up evidence.
        followup=bool(prev.get("followupObserved",False)) or int(prev.get("observationCount",0) or 0)>0 or sources>=2
        lifecycle=_evidence_lifecycle(age,e.get("status","CONFIRMED"),s.get("tier"),int(prev.get("observationCount",0) or 0)+1,sources,followup)
        base=float(s.get("evidenceWeight",0) or 0)
        # Aging factor affects monitoring weight only; it is not a probability.
        if lifecycle=="DECAYING": factor=0.70
        elif lifecycle=="EXPIRED": factor=0.35
        elif lifecycle=="PENDING_CONFIRMATION": factor=0.85
        else: factor=1.0
        rows.append({
            "dedupeKey":e.get("dedupeKey"),"title":e.get("title"),
            "publishedAt":s.get("publishedAt"),"ageDays":round(age,2) if age is not None else None,
            "lifecycle":lifecycle,"baseEvidenceWeight":round(base,3),
            "agingFactor":factor,"effectiveEvidenceWeight":round(min(1.0,base*factor),3),
            "independentSourceCount":sources,"followupObserved":followup,
            "interpretation":"生命周期用于降低陈旧证据对监测权重的影响，不代表该事件为真/假或任何发生概率。"
        })
    return rows

def _market_snapshot_now(dash):
    now=datetime.now(timezone.utc).isoformat()
    rows=[]
    for x in markets(dash or {}):
        rows.append({"name":x.get("name"),"value":x.get("value"),"change_pct":x.get("change_pct"),"observedAt":x.get("time") or x.get("updated") or now})
    return {"capturedAt":now,"markets":rows}

def persist_market_snapshot(dash,max_rows=720):
    """Append one immutable observation; bounded retention prevents unbounded file growth."""
    current=_market_snapshot_now(dash)
    old=read('market_snapshots.json',[])
    if isinstance(old,dict): old=old.get("snapshots",[])
    # Avoid duplicate writes during the same hour.
    hour=current["capturedAt"][:13]
    old=[x for x in old if str(x.get("capturedAt",""))[:13]!=hour]
    old.append(current)
    old=sorted(old,key=lambda x:x.get("capturedAt",""))[-max_rows:]
    MARKET_SNAPSHOTS.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding="utf-8")
    return old

def _market_baseline(snapshots, event_time, days=7):
    """Simple observational baseline from snapshots before the event."""
    vals={}
    for s in snapshots:
        t=dt(s.get("capturedAt"))
        if not t or not event_time: continue
        delta=(event_time-t).total_seconds()/86400
        if 0 < delta <= days:
            for m in s.get("markets",[]):
                try:
                    if m.get("change_pct") is not None:
                        vals.setdefault(str(m.get("name")),[]).append(float(m["change_pct"]))
                except Exception:
                    pass
    return {k:sum(v)/len(v) for k,v in vals.items() if v}

def build_time_window_validation(scenarios, historical_events):
    """Validate trigger evidence across event-relative windows using only observed later evidence."""
    windows=[("T1D",1),("T3D",3),("T7D",7),("T30D",30),("T90D",90),("T1Y",365)]
    events=historical_events or []
    parsed=[]
    for e in events:
        t=dt(e.get("source",{}).get("publishedAt"))
        if t: parsed.append((e,t))
    out=[]
    for s in scenarios or []:
        drivers=[x for x in s.get("evidenceDrivers",[]) if x.get("kind")=="EVENT"]
        rows=[]
        for d in drivers:
            e=next((x for x in events if str(x.get("id"))==str(d.get("id"))),None)
            if not e: continue
            t=dt(e.get("source",{}).get("publishedAt"))
            if not t: continue
            for code,days in windows:
                end=t+timedelta(days=days)
                later=[x for x,xt in parsed if t < xt <= end and str(x.get("id"))!=str(e.get("id"))]
                # A later event is treated only as an independent follow-up observation when its source differs.
                source_ids=set()
                for x in later:
                    sm=x.get("source",{}) or {}
                    source_ids.add(str(x.get("sourceIdentity") or sm.get("provider") or "UNKNOWN"))
                corroborating=[x for x in later if str(x.get("category","")).upper()==str(e.get("category","")).upper()]
                rows.append({
                    "driverId":d.get("id"),"driverTitle":d.get("title"),
                    "window":code,"startAt":t.isoformat(),"endAt":end.isoformat(),
                    "status":"OBSERVED" if later else "NO_FOLLOWUP_OBSERVED",
                    "followupEventCount":len(later),
                    "sameCategoryFollowupCount":len(corroborating),
                    "independentSourceCount":len(source_ids),
                    "evidenceIds":[x.get("id") for x in later[:8]],
                    "interpretation":"后续事件仅作为时间相关的独立观察；不据此认定因果或预测成立。"
                })
        summary={}
        for code,_ in windows:
            rr=[x for x in rows if x["window"]==code]
            summary[code]={
                "driversObserved":sum(1 for x in rr if x["status"]=="OBSERVED"),
                "followupEvents":sum(x["followupEventCount"] for x in rr),
                "sameCategoryFollowups":sum(x["sameCategoryFollowupCount"] for x in rr),
                "independentSources":sum(x["independentSourceCount"] for x in rr)
            }
        out.append({"scenarioCode":s.get("code"),"windows":summary,"details":rows[:60],"method":"事件发生后按固定时间窗检查后续公开事件；缺失数据不回填。","causalStatus":"NOT_ESTABLISHED"})
    return out

def build_trigger_calibration(scenarios, historical_events):
    """Historical descriptive counts for trigger reliability; not probabilities."""
    buckets={}
    for e in historical_events or []:
        metrics=e.get("anomalyAnalysis",{}).get("metrics",[])
        signal="ELEVATED_DEVIATION" if any(x.get("signal")=="ELEVATED_DEVIATION" for x in metrics) else ("WATCH" if any(x.get("signal")=="WATCH" for x in metrics) else "WITHIN_BASELINE")
        for s in scenarios or []:
            ids={str(x.get("id")) for x in s.get("evidenceDrivers",[]) if x.get("kind")=="EVENT"}
            if e.get("eventId") not in ids: continue
            for d in s.get("evidenceDrivers",[]):
                if d.get("kind")!="EVENT" or str(d.get("id"))!=str(e.get("eventId")): continue
                key=str(d.get("category") or d.get("role") or "UNKNOWN_TRIGGER")
                b=buckets.setdefault(key,{"trigger":key,"observations":0,"followup":0,"signals":{"WITHIN_BASELINE":0,"WATCH":0,"ELEVATED_DEVIATION":0}})
                b["observations"]+=1
                if any(w.get("status")=="OBSERVED" for w in e.get("windows",[])): b["followup"]+=1
                b["signals"][signal]+=1
    out=[]
    for b in buckets.values():
        n=b["observations"]; strong=b["signals"]["ELEVATED_DEVIATION"]
        b["historicalSignalRate"]=round(strong/n,3) if n else None
        b["calibrationWeight"]=round(min(1.0,0.35+0.65*(strong/n)),3) if n>=3 else 0.5
        b["status"]="CALIBRATED" if n>=3 else "INSUFFICIENT_SAMPLE"
        b["interpretation"]="历史描述性指标，仅用于调整监测权重；不是发生概率、胜率或因果估计。"
        out.append(b)
    return sorted(out,key=lambda x:(x["status"]!="CALIBRATED",-x["observations"],x["trigger"]))

def build_retrospective_calibration(scenarios, historical_events):
    """Record post-hoc observations without treating them as forecasts or causal proof."""
    rows=[]
    for s in scenarios or []:
        code=s.get("code")
        evidence=set(str(x.get("id")) for x in s.get("evidenceDrivers",[]) if x.get("kind")=="EVENT")
        related=[e for e in (historical_events or []) if e.get("eventId") in evidence]
        observed=sum(1 for e in related if any(w.get("status")=="OBSERVED" for w in e.get("windows",[])))
        deviations=sum(1 for e in related for x in e.get("anomalyAnalysis",{}).get("metrics",[]) if x.get("signal")=="ELEVATED_DEVIATION")
        rows.append({
            "scenarioCode":code,
            "eventCount":len(related),
            "eventsWithFollowup":observed,
            "elevatedMarketDeviationCount":deviations,
            "calibrationStatus":"EARLY_SAMPLE" if observed<3 else "HISTORICAL_SAMPLE",
            "interpretation":"用于事后校准触发器与证据权重；不表示该剧本发生概率或因果成立。"
        })
    return rows

def build_event_market_anomalies(event, windows, snapshots):
    pub=dt(event.get("source",{}).get("publishedAt"))
    if not pub: return {"status":"EVENT_TIME_UNKNOWN","metrics":[]}
    baseline=_market_baseline(snapshots,pub,7)
    metrics=[]
    for w in windows:
        if w.get("window")=="T0" or w.get("status")!="OBSERVED": continue
        for m in w.get("markets",[]):
            name=str(m.get("name")); cp=m.get("change_pct")
            if cp is None: continue
            b=baseline.get(name)
            if b is None: continue
            delta=round(float(cp)-b,3)
            metrics.append({"window":w.get("window"),"name":name,"observedChangePct":cp,"baseline7dAvgChangePct":round(b,3),"deviationPctPoints":delta,"signal":"ELEVATED_DEVIATION" if abs(delta)>=1.5 else ("WATCH" if abs(delta)>=0.5 else "WITHIN_BASELINE")})
    return {"status":"OBSERVATIONAL_ONLY","baselineWindow":"T-7D→T-1D","metrics":metrics,"causalStatus":"NOT_ESTABLISHED"}

def build_historical_market_windows(event, snapshots):
    """Use only snapshots whose timestamps are actually observed; never backfill missing history."""
    pub=dt(event.get("source",{}).get("publishedAt"))
    if not pub:return []
    targets=[("T0",0),("T1D",1),("T3D",3),("T7D",7),("T30D",30),("T90D",90),("T1Y",365)]
    out=[]
    for code,days in targets:
        target=pub+timedelta(days=days)
        candidates=[s for s in snapshots if dt(s.get("capturedAt"))]
        candidates.sort(key=lambda s:abs((dt(s["capturedAt"])-target).total_seconds()))
        chosen=candidates[0] if candidates and target <= datetime.now(timezone.utc) and abs((dt(candidates[0]["capturedAt"])-target).total_seconds())<=18*3600 else None
        out.append({"window":code,"targetAt":target.isoformat(),"capturedAt":chosen.get("capturedAt") if chosen else None,"status":"OBSERVED" if chosen else "MISSING","markets":chosen.get("markets",[]) if chosen else []})
    return out

def build_transmission_windows(global_events, snapshots):
    """Create event-relative market windows from immutable observed snapshots; never reuse today's market data for future windows."""
    names=("USD/CNY","黄金","美国10年期收益率","布伦特原油","VIX","上证指数","沪深300","标普500")
    windows=[("T0","事件当日",0),("T1D","T+1天",1),("T3D","T+3天",3),("T7D","T+7天",7),("T30D","T+30天",30)]
    snap=list(snapshots or [])
    out=[]
    for e in (global_events or [])[:12]:
        pub=dt(e.get("source",{}).get("publishedAt"))
        obs=[]
        for code,label,offset in windows:
            metrics=[]; chosen=None
            if pub:
                target=pub+timedelta(days=offset)
                candidates=[s for s in snap if dt(s.get("capturedAt")) and target <= datetime.now(timezone.utc) and abs((dt(s["capturedAt"])-target).total_seconds())<=18*3600]
                if candidates:
                    chosen=min(candidates,key=lambda s:abs((dt(s["capturedAt"])-target).total_seconds()))
            by={str(x.get("name")):x for x in (chosen.get("markets",[]) if chosen else [])}
            for name in names:
                m=by.get(name)
                if not m: continue
                metrics.append({"name":name,"value":m.get("value"),"change_pct":m.get("change_pct"),"observedAt":m.get("observedAt") or (chosen or {}).get("capturedAt"),"status":"AVAILABLE","source":"market_snapshot"})
            obs.append({"window":code,"label":label,"offsetDays":offset,"metrics":metrics,"capturedAt":(chosen or {}).get("capturedAt"),"status":"OBSERVATION_ONLY" if chosen else "MISSING"})
        out.append({
            "eventId":e.get("id"),"dedupeKey":e.get("dedupeKey"),"title":e.get("title"),
            "eventPublishedAt":e.get("source",{}).get("publishedAt"),"eventTimeKnown":pub is not None,
            "windows":obs,
            "method":"相对事件时间窗只读取实际保存的市场快照；没有对应历史快照就保持缺失，不用当前数据回填 T+1/T+3/T+7/T+30。",
            "causalStatus":"NOT_ESTABLISHED"
        })
    return out

SCENARIO_VALIDATION_HISTORY=ROOT/'scenario_validation_history.json'

def persist_validation_history(scenarios,historical_events,max_rows=720):
    """Persist compact cross-run validation observations so later runs can validate the same trigger without relying on the previous run only."""
    old=read('scenario_validation_history.json',[])
    if isinstance(old,dict): old=old.get('rows',[])
    now=datetime.now(timezone.utc).isoformat()
    rows=[]
    for s in scenarios or []:
        for d in [x for x in s.get('evidenceDrivers',[]) if x.get('kind')=='EVENT']:
            e=next((x for x in (historical_events or []) if str(x.get('eventId'))==str(d.get('id'))),None)
            if not e: continue
            windows=[w for w in e.get('windows',[]) if w.get('status')=='OBSERVED']
            rows.append({
                'recordedAt':now,'scenarioCode':s.get('code'),'driverId':d.get('id'),
                'driverTitle':d.get('title'),'category':d.get('category'),'dedupeKey':e.get('dedupeKey'),
                'eventPublishedAt':e.get('eventPublishedAt'),'followupWindows':[w.get('window') for w in windows],
                'followupObserved':bool(windows),
                'marketObservedWindows':[w.get('window') for w in e.get('windows',[]) if w.get('status')=='OBSERVED'],
                'sourceCount':int((e.get('corroboration') or {}).get('independentSourceCount',0) or 0)
            })
    # One row per run/driver; keep bounded history.
    old.extend(rows)
    old=sorted(old,key=lambda x:x.get('recordedAt',''))[-max_rows:]
    SCENARIO_VALIDATION_HISTORY.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
    return old

def build_cross_run_validation(scenarios,history):
    """Aggregate durable observations across many runs; descriptive only, never a probability."""
    hist=history or []
    out=[]
    for s in scenarios or []:
        for d in [x for x in s.get('evidenceDrivers',[]) if x.get('kind')=='EVENT']:
            key=str(d.get('id'))
            rr=[x for x in hist if str(x.get('driverId'))==key]
            if not rr: continue
            out.append({
                'scenarioCode':s.get('code'),'driverId':key,'driverTitle':d.get('title'),
                'runObservationCount':len(rr),
                'firstObservedAt':min((x.get('recordedAt') for x in rr),default=None),
                'followupRunCount':sum(1 for x in rr if x.get('followupObserved')),
                'marketObservedRunCount':sum(1 for x in rr if x.get('marketObservedWindows')),
                'maxIndependentSourceCount':max((int(x.get('sourceCount',0) or 0) for x in rr),default=0),
                'observedWindows':sorted(set(w for x in rr for w in x.get('followupWindows',[]))),
                'status':'MULTI_RUN_OBSERVED' if len(rr)>=2 else 'SINGLE_RUN',
                'method':'跨运行持久化的后续观察计数；用于描述性校准，不代表概率、因果或预测成立。'
            })
    return out

def build_scenario_snapshot(scenarios,global_events=None):
    """Compact audit snapshot for UI/history consumers; no probabilities are implied."""
    previous_snapshot=None
    try:
        previous_snapshot=json.loads(OUT.read_text(encoding="utf-8")).get("scenarioSnapshot")
    except Exception:
        previous_snapshot=None
    lifecycle=build_evidence_lifecycle(global_events or [],previous_snapshot)
    lifecycle_map={str(x.get('dedupeKey')):x for x in lifecycle if x.get('dedupeKey')}
    registry=_merge_evidence_registry(global_events or [],previous_snapshot)
    graph=build_evidence_graph(global_events or [],scenarios,lifecycle)
    for r in registry:
        x=lifecycle_map.get(str(r.get('dedupeKey')))
        if x:
            r.update({'lifecycle':x.get('lifecycle'),'agingFactor':x.get('agingFactor'),'effectiveEvidenceWeight':x.get('effectiveEvidenceWeight'),'followupObserved':x.get('followupObserved',False)})
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "evidenceRegistry": registry,
        "evidenceLifecycle": lifecycle,
        "evidenceGraph": graph,
        "eventEvidence": [{"id":e.get("id"),"title":e.get("title"),"publishedAt":e.get("source",{}).get("publishedAt"),"fetchedAt":e.get("source",{}).get("fetchedAt"),"tier":e.get("source",{}).get("tier"),"freshness":e.get("source",{}).get("freshness"),"dedupeKey":e.get("dedupeKey"),"lifecycle":e.get("source",{}).get("lifecycle"),"evidenceWeight":e.get("source",{}).get("evidenceWeight"),"corroboration":e.get("corroboration")} for e in (global_events or [])],
        "scenarios": [
            {
                "id": s.get("id"), "code": s.get("code"),
                "activationState": s.get("activationState","WATCH"),
                "triggerScore": s.get("triggerScore",0),
                "triggerEvidence": s.get("triggerEvidence",[]),
                "counterSignals": s.get("counterSignals",[]),
                "evidenceDrivers": s.get("evidenceDrivers",[])
            } for s in scenarios
        ]
    }

def build_scenario_history(current_snapshot):
    """Explain changes between consecutive monitoring runs using observable component deltas."""
    previous=None
    try: previous=json.loads(OUT.read_text(encoding="utf-8")).get("scenarioSnapshot")
    except Exception: pass
    if not previous or not previous.get("scenarios"):
        return {"baseline":"FIRST_RUN","previousGeneratedAt":None,"changes":[]}
    old={str(x.get("code")):x for x in previous.get("scenarios",[])}
    old_events={str(x.get("dedupeKey")):x for x in previous.get("eventEvidence",[]) if x.get("dedupeKey")}
    cur_events={str(x.get("dedupeKey")):x for x in current_snapshot.get("eventEvidence",[]) if x.get("dedupeKey")}
    old_reg={str(x.get("dedupeKey")):x for x in previous.get("evidenceRegistry",[]) if x.get("dedupeKey")}
    cur_reg={str(x.get("dedupeKey")):x for x in current_snapshot.get("evidenceRegistry",[]) if x.get("dedupeKey")}
    corroborated=[]; lifecycle_changes=[]
    for k,v in cur_reg.items():
        p=old_reg.get(k)
        if not p: continue
        if int(v.get("independentSourceCount",0))>int(p.get("independentSourceCount",0)):
            corroborated.append({"dedupeKey":k,"title":v.get("title"),"from":p.get("independentSourceCount",0),"to":v.get("independentSourceCount",0)})
        if v.get("lifecycle")!=p.get("lifecycle"):
            lifecycle_changes.append({"dedupeKey":k,"title":v.get("title"),"from":p.get("lifecycle"),"to":v.get("lifecycle")})
    added_events=[v for k,v in cur_events.items() if k not in old_events]
    removed_events=[v for k,v in old_events.items() if k not in cur_events]
    changes=[]
    for cur in current_snapshot.get("scenarios",[]):
        code=str(cur.get("code")); p=old.get(code)
        if not p: continue
        delta=round(float(cur.get("triggerScore",0))-float(p.get("triggerScore",0)),2)
        old_drivers={str(x.get("id") or x.get("name")):x for x in p.get("evidenceDrivers",[])}
        cur_drivers={str(x.get("id") or x.get("name")):x for x in cur.get("evidenceDrivers",[])}
        added=[v for k,v in cur_drivers.items() if k not in old_drivers]
        removed=[v for k,v in old_drivers.items() if k not in cur_drivers]
        corroborated_local=[]
        for k,v in cur_drivers.items():
            q=old_drivers.get(k)
            if q and v.get("kind")=="EVENT":
                a=float(q.get("evidenceWeight",0) or 0); b=float(v.get("evidenceWeight",0) or 0)
                if b>a+0.05: corroborated_local.append({"id":k,"title":v.get("title"),"from":a,"to":b})
        counter=cur.get("counterSignalAnalysis",{})
        prev_counter=p.get("counterSignalAnalysis",{})
        counter_delta=round(float(counter.get("strength",0) or 0)-float(prev_counter.get("strength",0) or 0),3)
        reasons=[]
        if added: reasons.append({"type":"NEW_EVIDENCE","direction":"UP","magnitude":len(added),"items":[x.get("title") for x in added[:5]]})
        if corroborated_local or corroborated: reasons.append({"type":"CORROBORATION","direction":"UP","magnitude":len(corroborated_local)+len(corroborated),"items":[x.get("title") for x in (corroborated_local+corroborated)[:5]]})
        if removed: reasons.append({"type":"EVIDENCE_REMOVED","direction":"DOWN","magnitude":len(removed),"items":[x.get("title") for x in removed[:5]]})
        if counter_delta>0: reasons.append({"type":"COUNTER_SIGNAL","direction":"DOWN","magnitude":counter_delta,"items":[x.get("title") for x in (counter.get("signals") or [])[:5]]})
        if counter_delta<0: reasons.append({"type":"COUNTER_SIGNAL_WEAKENED","direction":"UP","magnitude":abs(counter_delta),"items":[]})
        if cur.get("triggerEvidence")!=p.get("triggerEvidence"): reasons.append({"type":"TRIGGER_EVIDENCE_CHANGE","direction":"MIXED","magnitude":1,"items":cur.get("triggerEvidence",[])[:5]})
        if cur.get("activationState")!=p.get("activationState"): reasons.append({"type":"STATE_CHANGE","direction":"MIXED","magnitude":1,"items":[str(p.get("activationState"))+" → "+str(cur.get("activationState"))]})
        changes.append({"id":cur.get("id"),"code":code,"previousState":p.get("activationState","WATCH"),"currentState":cur.get("activationState","WATCH"),"previousScore":p.get("triggerScore",0),"currentScore":cur.get("triggerScore",0),"delta":delta,"explanation":{"scoreDelta":delta,"components":reasons,"interpretation":"变化解释基于相邻运行的可观察证据差异，不表示因果关系或发生概率。"}})
    return {"baseline":"COMPARISON","previousGeneratedAt":previous.get("generatedAt"),"changes":changes,"newEvidence":added_events[:20],"staleOrRemovedEvidence":removed_events[:20],"corroboratedEvidence":corroborated[:20],"lifecycleChanges":lifecycle_changes[:20]}

def build_dynamic_tree(news,dash=None):
    previous_snapshot=None
    try: previous_snapshot=json.loads(OUT.read_text(encoding="utf-8")).get("scenarioSnapshot")
    except Exception: pass
    trigger_calibration=(previous_snapshot or {}).get("triggerCalibration",[])
    ge=build_global_events(news)
    root=ge[0]["id"] if ge else "evt-none"
    ids=[x["id"] for x in ge[:8]]
    responses=[
      {"id":"resp-cn-r1","round":1,"actor":"CN","responseType":"POLICY","title":"中国第1轮应对","description":"围绕供应链、贸易伙伴、能源与产业政策工具进行响应。","triggerEventIds":ids,"expectedTargets":["供应链","贸易","能源"],"intensity":0.55,"expectedTiming":"T7D","impacts":{"trade":0.15,"currency":-0.05,"equities":0,"bonds":0.05,"commodities":0.1,"crypto":0,"logistics":0.2},"confidence":"MEDIUM"},
      {"id":"resp-us-r2","round":2,"actor":"US","responseType":"POLICY","title":"美国第2轮加码/施压","description":"若中国响应改变贸易或技术路径，美国可能通过贸易、技术或投资工具继续施压。","triggerEventIds":ids,"expectedTargets":["技术","资本","贸易"],"intensity":0.55,"expectedTiming":"T15D","impacts":{"trade":-0.25,"currency":-0.1,"equities":-0.15,"bonds":0.1,"commodities":0.15,"crypto":0,"logistics":-0.1},"confidence":"MEDIUM"},
      {"id":"resp-cn-r3","round":3,"actor":"CN","responseType":"DIPLOMACY","title":"中国第3轮多剧本","description":"根据第2轮压力分化为硬碰撞、结构性谈判或第三方迂回三条条件路径。","triggerEventIds":ids,"expectedTargets":["贸易","产业","第三方市场"],"intensity":0.65,"expectedTiming":"T30D","impacts":{"trade":0.05,"currency":0,"equities":0,"bonds":0.05,"commodities":0.1,"crypto":0,"logistics":0.15},"confidence":"MEDIUM"}
    ]
    specs=[
      ("scenario-a","HARD_DECOUPLING","A","全面脱钩 / 硬碰撞","新增强制措施同时扩大到贸易、技术或资本渠道。",0.60),
      ("scenario-b","STRUCTURAL_NEGOTIATION","B","结构性谈判 / 局部缓和","竞争继续，但出现可核验的沟通、豁免、延期或执行强度下降。",0.50),
      ("scenario-c","THIRD_PARTY_DIVERSION","C","第三方迂回 / 市场转移","贸易、生产或资金流通过第三方市场重新配置，同时合规要求提高。",0.58)
    ]
    scenarios=[]
    market_by_name={str(x.get("name")):x for x in markets(dash or {})}
    def drivers_for(stype):
        drivers=[]
        for e in ge[:6]:
            cat=str(e.get("category","")).upper()
            relevant=(stype=="HARD_DECOUPLING" and cat in ("TECHNOLOGY","TRADE","TARIFF","SANCTIONS","PAYMENT")) or (stype=="STRUCTURAL_NEGOTIATION" and cat in ("POLITICS","GEOPOLITICS","TRADE")) or (stype=="THIRD_PARTY_DIVERSION" and e.get("triggerRole")=="CATALYST")
            if relevant:
                drivers.append({"kind":"EVENT","id":e.get("id"),"title":e.get("title"),"source":e.get("source",{}).get("provider"),"url":e.get("source",{}).get("url"),"role":e.get("triggerRole"),"category":e.get("category"),"publishedAt":e.get("source",{}).get("publishedAt"),"fetchedAt":e.get("source",{}).get("fetchedAt"),"tier":e.get("source",{}).get("tier"),"freshness":e.get("source",{}).get("freshness"),"credibility":e.get("source",{}).get("credibility"),"lifecycle":e.get("source",{}).get("lifecycle"),"evidenceWeight":e.get("source",{}).get("evidenceWeight")})
        for name in ("USD/CNY","黄金","美国10年期收益率","布伦特原油","VIX"):
            m=market_by_name.get(name)
            if m:
                cp=m.get("change_pct")
                drivers.append({
                    "kind":"MARKET","name":name,"value":m.get("value"),"change_pct":cp,
                    "source":"dashboard",
                    "observationStatus":"DATA_PRESENT",
                    "observedAt":m.get("time") or m.get("updated") or m.get("date"),
                    "interpretation":"同期市场变化可用于验证是否出现伴随信号；不能单独证明事件造成该变化。"
                })
        return drivers[:10]
    for sid,stype,code,title,condition,sens in specs:
        chain=[
          {"id":f"{sid}-1","order":1,"actor":"CN","action":"第1轮应对","mechanism":"降低直接冲击并调整供应链","consequence":"第三方与美国相关方重新评估政策工具","nextNodeIds":[f"{sid}-2"],"affectedDomains":["TRADE","INVESTMENT"],"evidenceLevel":"INFERENCE","evidenceEventIds":ids,"caveat":"不是对未来行为的事实陈述；需由正式政策与执行证据验证。"},
          {"id":f"{sid}-2","order":2,"actor":"US","action":"第2轮加码/施压","mechanism":"通过贸易、技术、资本或规则工具改变成本","consequence":"中国进入第3轮路径选择","nextNodeIds":[f"{sid}-3"],"affectedDomains":["TRADE","INVESTMENT"],"evidenceLevel":"INFERENCE","evidenceEventIds":ids,"caveat":"只有出现新的正式措施或执行变化时才提高该节点监控权重。"},
          {"id":f"{sid}-3","order":3,"actor":"CN","action":title,"mechanism":condition,"consequence":"进入对应时间窗口并持续验证触发器","nextNodeIds":[],"affectedDomains":["TRADE","INVESTMENT","LIFE"],"evidenceLevel":"ASSUMPTION","evidenceEventIds":ids,"caveat":"剧本假设；不得当作已经发生的政策结果。"}
        ]
        act=_scenario_activation(ge,stype,trigger_calibration); drivers=drivers_for(stype); scenarios.append({"id":sid,"type":stype,"code":code,"title":title,"description":condition,"evidenceDrivers":drivers,"prerequisites":["至少一个第三方或中美事件被确认","存在可验证的政策响应"],"triggers":[{"condition":condition,"direction":"OCCUR"}],"chain":chain,"confidence":"MEDIUM","sensitivity":sens,"activationState":act["activationState"],"triggerScore":act["triggerScore"],"triggerEvidence":act["evidence"],"counterSignals":act["counterSignals"],"counterSignalAnalysis":_counter_signal_analysis(ge,stype),"recomputeIf":["出现新的正式政策文本","关键执行细则发生变化","第三方冲击解除或扩大","出现与当前路径相反的多源证据"],"horizons":_scenario_horizons(sid,stype)})
    snapshot=build_scenario_snapshot(scenarios,ge)
    snapshots=persist_market_snapshot(dash or {})
    snapshot["transmissionTimeline"]=build_transmission_windows(ge, snapshots)
    historical=[]
    for e in ge[:12]:
        ws=build_historical_market_windows(e,snapshots)
        historical.append(dict(e,windows=ws,anomalyAnalysis=build_event_market_anomalies(e,ws,snapshots)))
    snapshot["historicalMarketWindows"]=historical
    snapshot["retrospectiveCalibration"]=build_retrospective_calibration(scenarios,historical)
    snapshot["timeWindowValidation"]=build_time_window_validation(scenarios,historical)
    validation_history=persist_validation_history(scenarios,historical)
    snapshot["crossRunValidation"]=build_cross_run_validation(scenarios,validation_history)
    proposed_calibration=build_trigger_calibration(scenarios,historical)
    previous_audit=(previous_snapshot or {}).get("calibrationAudit",[])
    snapshot["triggerCalibration"],guard_audit=_calibration_guard(proposed_calibration,previous_audit)
    snapshot["calibrationAudit"]=guard_audit
    # Separate observation from causal attribution: market data can corroborate a transmission
    # signal only as a co-movement/validation observation, never as proof of causality.
    market_drivers=[d for s in scenarios for d in s.get("evidenceDrivers",[]) if d.get("kind")=="MARKET"]
    snapshot["transmissionValidation"]={
        "marketObservationCount":len(market_drivers),
        "eventObservationCount":len(ge),
        "status":"OBSERVATIONAL",
        "rule":"市场指标与事件同期变化只能作为伴随验证信号；缺少连续、可识别的实体数据时不做因果归因。",
        "observations":[
            {"scenarioCode":s.get("code"),"marketSignals":[
                {"name":d.get("name"),"change_pct":d.get("change_pct"),"observationStatus":d.get("observationStatus","DATA_PRESENT")}
                for d in s.get("evidenceDrivers",[]) if d.get("kind")=="MARKET"
            ]}
            for s in scenarios
        ]
    }
    history=build_scenario_history(snapshot)
    return {"schema_version":"2.0","globalEvents":ge,"responses":responses,"scenarioTree":{"id":"tree-"+datetime.now(timezone.utc).strftime("%Y%m%d"),"rootEventId":root,"title":"全球事件 → 中国第1轮 → 美国第2轮 → 中国第3轮多剧本","rounds":[{"round":1,"actor":"CN","title":"中国第1轮应对","responseIds":["resp-cn-r1"]},{"round":2,"actor":"US","title":"美国第2轮加码/施压","responseIds":["resp-us-r2"]},{"round":3,"actor":"CN","title":"中国第3轮多剧本","responseIds":["resp-cn-r3"]}],"scenarios":scenarios,"generatedAt":datetime.now(timezone.utc).isoformat(),"modelVersion":"dynamic-scenario-v2"},"time_horizons":[{"id":h[0],"label":h[1],"startOffsetDays":h[2],"endOffsetDays":h[3]} for h in HORIZONS],"action_domains":["INVESTMENT","TRADE","LIFE"],"scenarioSnapshot":snapshot,"scenarioHistory":history}

def scenario_task_registry():
    """Read durable task records when a backend or scheduled runner has written them."""
    raw=read('scenario_tasks.json',{})
    if isinstance(raw,list): return raw
    return raw.get('tasks',[]) if isinstance(raw,dict) else []

def build(news,dash,policy,social,ai):
 es=events(news); regs=Counter(x['region'] for x in es); ls=layer_state(news,dash,social)
 gov=governance_layer(news)
 ls.insert(7,{'id':'governance','name':'治理与人事网络','signal':f'近90日公开报道中检出 {len(gov)} 条反腐/审查相关信号；人物履历、任职地点与机构关系仅在有来源时记录','evidence':'news','caveat':'系统只记录公开、可核验履历，不据此推断政治派系归属或个人动机'})
 scenarios=[
 {'id':'base','name':'A · 基准路径','condition':'现有措施按当前节奏推进','chain':['政策执行','企业/政府响应','市场定价','产业链消化','社会反馈','下一轮政策']},
 {'id':'escalate','name':'B · 升级路径','condition':'出现新增强制措施或重大供给/安全扰动','chain':['新增措施','相关方反应','贸易/金融/能源成本','企业调整','民众体感变化','政策再反馈']},
 {'id':'ease','name':'C · 缓和路径','condition':'出现可验证的沟通、豁免、延期、撤回或执行强度下降','chain':['缓和信号','企业决策变化','风险溢价变化','供应链修复','社会体感反馈','政策确认']},
 {'id':'shock','name':'D · 外生冲击','condition':'出现当前资料未覆盖的重大突发事件','chain':['突发冲击','紧急响应','市场/物流先行','政策工具扩张','社会反馈','重建情景树']}
 ]
 signals=[
 {'name':'政策落地','trigger':'出现正式法令、法规、制裁、关税、出口管制及执行细则','why':'区分表态与可执行措施'},
 {'name':'市场—实体背离','trigger':'市场价格与就业、订单、消费等实体指标持续背离','why':'防止用单一市场信号解释现实'},
 {'name':'民众体感变化','trigger':'公开讨论主题持续转向就业、收入、住房、物价或消费且行为数据同步变化','why':'讨论与行为需要交叉验证'},
 {'name':'企业行为','trigger':'招聘、投资、订单、融资或供应链布局出现持续变化','why':'观察政策传导到实体经济的中间层'},
 {'name':'国际反应','trigger':'主要参与方出台对应措施或改变正式表述','why':'情景不能只看单一国家'},
 {'name':'治理/人事变化','trigger':'出现有正式来源的调查、免职、任命、判决或履历变化','why':'检查政策执行链和地方/行业项目是否同步变化，但不自动推断派系关系'},
 {'name':'地方项目洗牌信号','trigger':'相关地区公开出现项目暂停、调整、资金来源变化、负责人变更或规划修订','why':'用公开政策和项目证据验证是否存在结构性调整'},
 {'name':'反证信号','trigger':'核心假设被新数据、政策文本或实际执行结果否定','why':'触发重新推演而不是强行维持原结论'}
 ]
 red=['不要把“某人来自某地/曾任某职”直接当作政治派系证据；必须有明确、可靠来源才记录关系。','不要把反腐调查与地方项目变化的时间先后自动解释成因果关系；需要独立政策/项目证据。','不要根据籍贯、校友、任职经历等单一关系推断派系归属。','不要把公开评论/搜索结果当成总体民意；必须标明样本和选择偏差。','不要把新闻相关性当因果关系；要求至少一个独立验证信号。','不要把政策发布等同于政策执行，更不要把执行等同于效果。','不要把市场涨跌直接解释成资金迁徙，除非有连续资金流证据。','不要忽略企业与地方/行业之间的差异。','每条情景都要写出反证条件；反证出现就降低可信度并重建情景。','7天、30天、90天和1年尺度分开，不把短期冲击外推成长期结构。']
 base={'headline':'全局态势与多层社会反馈沙盘','executive_summary':'系统把公开事实、观察信号、模型推断、情景假设和未知分开。民众讨论仅作为信号，不代表总体民意；企业、资金、执行效果缺乏直接证据时保持未知。','state':{'china':{'event_count':regs.get('china',0)},'us':{'event_count':regs.get('us',0)},'global':{'event_count':regs.get('global',0)},'finance':{'market':markets(dash),'us_sector_risers':sectors(dash,'us_sector_market',True),'us_sector_fallers':sectors(dash,'us_sector_market',False)}},'layers':ls,'events':es,'governance':{'anti_corruption_signals':gov,'method':'documented public career/role links only; no faction attribution without explicit sourced evidence','regional_watch':[],'disruption_review':'对被查人员曾任职地区、行业与项目，仅检查是否存在公开可核验的政策/项目/人事变化；不把时间上的先后关系自动解释为因果关系'},'scenarios':scenarios,'signals':signals,'red_team':red,'action_framework':{'immediate':'只处理已确认、低成本、可逆事项；先记录证据。','watchlist':'监控政策落地、民众体感、企业行为、市场/资金、供应链、国际反应。','backup':'为不同情景准备可逆备用路径，不预设哪条一定发生。','stop':'核心假设被反证、数据质量异常或出现重大外生冲击时停止沿用旧情景并重算。'},'evidence':{'confirmed':'来源明确的政策、新闻和市场数据','signal':'公开讨论与行为变化等观察信号','inference':'影响链及跨层关联','assumption':'情景触发条件','unknown':'尚无足够公开证据验证的部分'},'social':social,'data_health':{'news_count':len(news),'ai_available':bool(ai),'dashboard_updated':dash.get('updated'),'policy_updated':policy.get('updated')},'generated_at':datetime.now(timezone.utc).isoformat(),'engine':'scenario-engine-v3-layered'}
 dynamic=build_dynamic_tree(news,dash)
 base['scenarioTasks']=scenario_task_registry()
 base['schema_version']='2.0'
 base['generatedAt']=base['generated_at']
 base['globalEvents']=dynamic['globalEvents']
 base['responses']=dynamic['responses']
 base['scenarioTree']=dynamic['scenarioTree']
 base['scenarioSnapshot']=dynamic['scenarioSnapshot']
 base['scenarioHistory']=dynamic['scenarioHistory']
 base['dynamic_scenarios']=dynamic['scenarioTree']['scenarios']
 base['time_horizons']=dynamic['time_horizons']
 base['action_domains']=dynamic['action_domains']
 base['dashboard']={'headline':base['headline'],'triggerEvents':[x['id'] for x in dynamic['globalEvents'][:5]],'activeScenarios':['scenario-a','scenario-b','scenario-c'],'immediateActions':['复核USD/CNY与流动性敞口','核算关税/物流成本','检查跨境支付通道','建立现金流预警线'],'warnings':['第三方转口必须通过原产地、海关、出口管制与制裁合规审查','情景是条件路径，不是确定性预测','单一市场价格不能单独证明资金迁徙']}
 return base
def ai_validate(base):
 if not KEY:return None
 prompt='你是中立的战略情报沙盘校验层。只使用输入JSON事实和信号，不引入外部事件。可改写executive_summary/layers/scenarios/signals/red_team/action_framework；必须保留不确定性、样本偏差和反证机制；不得做政治支持/反对评价、选举预测、投资买卖建议。输出完整合法JSON。输入：'+json.dumps(base,ensure_ascii=False)
 body={'model':MODEL,'messages':[{'role':'system','content':'中立、多源、证据分级的情景分析校验器'},{'role':'user','content':prompt}],'stream':False,'max_tokens':7000}
 try:
  req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(body,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json','User-Agent':'China-US-Global-Intelligence-Radar/Scenario-3.0'})
  raw=json.loads(urllib.request.urlopen(req,timeout=120).read().decode()); return json.loads(raw['choices'][0]['message']['content'])
 except Exception as e: print('Scenario AI error:',type(e).__name__); return None
def main():
 news=read('news.json',[]); dash=read('dashboard.json',{}); policy=read('policy_radar.json',{}); social=read('social_signals.json',{}); ai=read('ai_summaries.json',{})
 base=build(news,dash,policy,social,ai); x=ai_validate(base)
 if isinstance(x,dict):
  for k in ('events','state','social','data_health','layers'): x[k]=base[k]
  x['generated_at']=datetime.now(timezone.utc).isoformat(); x['engine']='scenario-engine-v3-ai-validated'; state=x
 else: state=base
 OUT.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8'); print('Scenario:',state['engine'],'layers=',len(state['layers']),'events=',len(state['events'])); return 0
if __name__=='__main__':sys.exit(main())
