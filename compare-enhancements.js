(()=>{
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const zh=n=>n.titleZh||n.title||'';
function render(){
 if(typeof data==='undefined')return;
 const el=$('compareMain'); if(!el)return;
 const mk=(label,region)=>{const a=data.filter(n=>n.region===region).slice().sort((x,y)=>(y.importance_score||0)-(x.importance_score||0)).slice(0,8);return `<div class="compare"><h3>${label}</h3><b>${a.length? a.length:'—'}</b><small>重点情报 · 按重要度排序</small><div class="compare-news">${a.map(n=>`<div class="compare-news-item"><span>${esc(n.importance_level||'B')}</span><a href="${n.url||'#'}" target="_blank" rel="noopener">${esc(zh(n))}</a><small>${esc(n.cat||'')} · 重要度 ${n.importance_score||0} · ${esc(n.sourceOrg||n.source||'')}</small></div>`).join('')||'<p>暂无重点情报</p>'}</div></div>`};
 el.innerHTML=mk('🇨🇳 中国重点信号','china')+mk('🇺🇸 美国重点信号','us');
}
setTimeout(render,1200);setInterval(render,5000);
})();