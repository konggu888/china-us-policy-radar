import json,os,urllib.request,sys,re
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'scenario_state.json'
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
 {'name':'地方项目洗牌信号','trigger':'相关地区公开出现项目暂停、调整、资金来源变化、负责人变更或规划修订','why':'用公开政策和项目证据验证是否存在结构性调整'}
 {'name':'反证信号','trigger':'核心假设被新数据、政策文本或实际执行结果否定','why':'触发重新推演而不是强行维持原结论'}
 ]
 red=['不要把“某人来自某地/曾任某职”直接当作政治派系证据；必须有明确、可靠来源才记录关系。','不要把反腐调查与地方项目变化的时间先后自动解释成因果关系；需要独立政策/项目证据。','不要根据籍贯、校友、任职经历等单一关系推断派系归属。','不要把公开评论/搜索结果当成总体民意；必须标明样本和选择偏差。','不要把新闻相关性当因果关系；要求至少一个独立验证信号。','不要把政策发布等同于政策执行，更不要把执行等同于效果。','不要把市场涨跌直接解释成资金迁徙，除非有连续资金流证据。','不要忽略企业与地方/行业之间的差异。','每条情景都要写出反证条件；反证出现就降低可信度并重建情景。','7天、30天、90天和1年尺度分开，不把短期冲击外推成长期结构。']
 base={'headline':'全局态势与多层社会反馈沙盘','executive_summary':'系统把公开事实、观察信号、模型推断、情景假设和未知分开。民众讨论仅作为信号，不代表总体民意；企业、资金、执行效果缺乏直接证据时保持未知。','state':{'china':{'event_count':regs.get('china',0)},'us':{'event_count':regs.get('us',0)},'global':{'event_count':regs.get('global',0)},'finance':{'market':markets(dash),'us_sector_risers':sectors(dash,'us_sector_market',True),'us_sector_fallers':sectors(dash,'us_sector_market',False)}},'layers':ls,'events':es,'governance':{'anti_corruption_signals':gov,'method':'documented public career/role links only; no faction attribution without explicit sourced evidence','regional_watch':[],'disruption_review':'对被查人员曾任职地区、行业与项目，仅检查是否存在公开可核验的政策/项目/人事变化；不把时间上的先后关系自动解释为因果关系'},'scenarios':scenarios,'signals':signals,'red_team':red,'action_framework':{'immediate':'只处理已确认、低成本、可逆事项；先记录证据。','watchlist':'监控政策落地、民众体感、企业行为、市场/资金、供应链、国际反应。','backup':'为不同情景准备可逆备用路径，不预设哪条一定发生。','stop':'核心假设被反证、数据质量异常或出现重大外生冲击时停止沿用旧情景并重算。'},'evidence':{'confirmed':'来源明确的政策、新闻和市场数据','signal':'公开讨论与行为变化等观察信号','inference':'影响链及跨层关联','assumption':'情景触发条件','unknown':'尚无足够公开证据验证的部分'},'social':social,'data_health':{'news_count':len(news),'ai_available':bool(ai),'dashboard_updated':dash.get('updated'),'policy_updated':policy.get('updated')},'generated_at':datetime.now(timezone.utc).isoformat(),'engine':'scenario-engine-v3-layered'}
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
