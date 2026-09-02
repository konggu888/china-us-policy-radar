import json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
NEWS=DATA/'news.json'
OUT=DATA/'policy_radar.json'

try:
    news=json.loads(NEWS.read_text(encoding='utf-8'))
except Exception:
    news=[]

SOURCE_MATRIX=[
    ('中国政府网','gov.cn','国务院/政策原文'),('国家发展改革委','ndrc.gov.cn','宏观、投资、产业政策'),
    ('中国人民银行','pbc.gov.cn','货币、金融、人民币'),('金融监管总局','nfra.gov.cn','银行保险监管'),
    ('中国证监会','csrc.gov.cn','资本市场监管'),('国家外汇局','safe.gov.cn','外汇、跨境资本'),
    ('工业和信息化部','miit.gov.cn','制造业、产业、AI/通信'),('科技部','most.gov.cn','科技创新、科研政策'),
    ('国家能源局','nea.gov.cn','能源、电力、油气'),('商务部','mofcom.gov.cn','外贸、外资、消费、供应链'),
    ('海关总署','customs.gov.cn','进出口、商品与贸易数据'),('外交部','mfa.gov.cn','外交政策与国际关系'),
    ('国防部','mod.gov.cn','国防与军事政策'),('国家统计局','stats.gov.cn','宏观与行业统计'),
    ('财政部','mof.gov.cn','财政、税收、政府债务'),('国家网信办','cac.gov.cn','数据、网络、平台治理'),
    ('新华社','xinhuanet.com','政策语言/权威新闻表述'),('人民日报','people.com.cn','政策语言/主流舆论表述')
]

LANGUAGE={
 '稳增长':['稳增长','growth support','stimulus'],
 '扩大内需':['扩大内需','domestic demand','消费','consumption'],
 '新质生产力':['新质生产力','new quality productive forces'],
 '人工智能+':['人工智能+','AI+','artificial intelligence'],
 '产业升级':['产业升级','industrial upgrading','manufacturing'],
 '科技自立自强':['科技自立自强','technological self-reliance'],
 '扩大开放':['扩大开放','外资','investment','open economy'],
 '风险防控':['风险防控','financial risk','risk prevention'],
 '国家安全':['国家安全','national security','security'],
 '贸易限制':['关税','出口管制','贸易限制','tariff','export control','trade restriction']
}

def hits(terms):
    return sum(1 for n in news if any(t.lower() in (n.get('title','')+' '+n.get('cat','')).lower() for t in terms))

language=[]
for k,terms in LANGUAGE.items():
    total=hits(terms)
    recent=sum(1 for n in news if any(t.lower() in (n.get('title','')+' '+n.get('cat','')).lower() for t in terms) and n.get('time','') >= (datetime.now(timezone.utc).strftime('%Y-%m-%d')))
    language.append({'keyword':k,'count':total,'recent':recent,'signal':'升温' if recent>=2 else '常态','method':'公开标题/文本中的关键词频次，属于描述性信号，不代表政策意图。'})

areas={
 '宏观/财政':['经济','财政','稳增长','扩大内需','政府债务','税'],
 '货币/金融':['金融','央行','利率','银行','证券','外汇','人民币'],
 '房地产/消费':['房地产','住房','消费','内需'],
 '产业/制造':['产业','制造','工信','工业'],
 'AI/半导体':['AI','人工智能','芯片','半导体','科技'],
 '能源/资源':['能源','石油','天然气','电力','稀土','资源'],
 '外贸/外资':['贸易','关税','出口','进口','外资','供应链'],
 '外交/国防/安全':['外交','国防','军事','国家安全','网络安全']
}
area_rows=[]
for name,terms in areas.items():
    matched=[n for n in news if any(t.lower() in (n.get('title','')+' '+n.get('cat','')).lower() for t in terms)]
    area_rows.append({'name':name,'signals':len(matched),'high_risk':sum(n.get('risk') in ('高','极高') for n in matched),'latest':max((n.get('time','') for n in matched),default='')})
area_rows.sort(key=lambda x:x['signals'],reverse=True)

policy_items=[]
for n in news:
    if n.get('sourceType')=='official' or n.get('cat') in ('经济','金融','产业','科技 / AI','贸易 / 供应链','能源 / 资源','国家安全','国防','外交'):
        policy_items.append({
            'title':n.get('title',''),'url':n.get('url',''),'date':n.get('time',''),'agency':n.get('sourceOrg') or n.get('source',''),
            'category':n.get('cat',''),'risk':n.get('risk',''),'verification':n.get('verification',''),
            'impact_industry':n.get('impact_industry',[]),'short_term':n.get('short_term',''),'long_term':n.get('long_term',''),
            'watch_data':n.get('watch_data',[]),'policy_level':n.get('policy_level','常规跟踪')
        })
policy_items=sorted(policy_items,key=lambda x:(x['date'],x['risk']),reverse=True)[:30]

obj={
 'updated':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
 'source_matrix':[{'agency':a,'domain':d,'focus':f} for a,d,f in SOURCE_MATRIX],
 'language_radar':language,
 'policy_areas':area_rows,
 'policy_chain':{
   'steps':['政策原文','财政/金融支持','企业/行业行动','商品/价格/订单','海关/统计数据','执行效果验证'],
   'status':['发现政策','等待支持数据','等待企业行动','等待价格/订单','等待统计数据','等待独立验证'],
   'rule':'只有出现后续独立数据或企业/行业行动，才提高“执行效果”可信度；政策发布本身不等于政策有效。'
 },
 'policy_items':policy_items,
 'analysis_schema':['发生了什么','原始政策','影响领域','影响国家','短期影响','中长期影响','需要继续观察的数据','来源验证等级']
}
OUT.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
print('wrote',OUT)
