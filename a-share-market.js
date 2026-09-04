(()=>{
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function pct(v){return v==null?'—':`${v>0?'+':''}${v}%`}
function card(x,label){const v=Number(x.weekly_pct??x.change_pct);return `<article class="market-card"><div><b>${esc(x.name)}</b><small>${esc(label)}</small></div><strong class="${v>0?'up':v<0?'down':'flat'}">${pct(v)}</strong><span>${x.up_count!=null?`上涨 ${esc(x.up_count)} · 下跌 ${esc(x.down_count??'—')} · 领涨 ${esc(x.leader||'—')}`:`本周涨跌幅 · 数据截至 ${esc(x.asof||x.weekly_period||'—')}`}</span></article>`}
let lastSignature='';
async function render(){const el=$('compareMarket');if(!el)return;try{const r=await fetch('data/market_sectors.json?ts='+Date.now(),{cache:'no-store'});const d=await r.json();const aup=(d.a_share_weekly_risers||[]).slice(0,5),adown=(d.a_share_weekly_fallers||[]).slice(0,5);const up=(d.weekly_risers||[]).slice(0,5),down=(d.weekly_fallers||[]).slice(0,5);const sig=JSON.stringify([d.updated,aup.map(x=>[x.code,x.name,x.weekly_pct]),adown.map(x=>[x.code,x.name,x.weekly_pct]),up.map(n=>[n,d.sectors?.[n]?.weekly_pct]),down.map(n=>[n,d.sectors?.[n]?.weekly_pct])]);if(sig===lastSignature)return;lastSignature=sig;
const aupHtml=aup.map(x=>card(x,'A股行业板块')).join(''), adownHtml=adown.map(x=>card(x,'A股行业板块')).join('');
const usUpHtml=up.map(n=>card({name:n,weekly_pct:d.sectors?.[n]?.weekly_pct,asof:d.sectors?.[n]?.asof},'美股行业ETF代理')).join(''), usDownHtml=down.map(n=>card({name:n,weekly_pct:d.sectors?.[n]?.weekly_pct,asof:d.sectors?.[n]?.asof},'美股行业ETF代理')).join('');
el.innerHTML=`<div class="market-board"><div class="market-section"><h3>🇨🇳 A股本周上涨板块</h3>${aupHtml||'<p>暂无A股行业周度数据</p>'}</div><div class="market-section"><h3>🇨🇳 A股本周下跌板块</h3>${adownHtml||'<p>暂无A股行业周度数据</p>'}</div><div class="market-section"><h3>🇺🇸 美股本周上涨板块</h3>${usUpHtml||'<p>暂无数据</p>'}</div><div class="market-section"><h3>🇺🇸 美股本周下跌板块</h3>${usDownHtml||'<p>暂无数据</p>'}</div></div><small class="market-note">A股按东方财富行业板块周K线本周涨跌幅排序；美股按11个行业ETF近5个交易日表现排序。数据时间：${esc(d.updated||'')}。</small>`
}catch(e){console.warn('market board',e)}}
setTimeout(render,1200);setInterval(render,30000);
})();
