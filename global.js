(()=>{
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cats=['政治','金融','经济','产业','科技 / AI','国防','内政','国家安全','外交','贸易 / 供应链','能源 / 资源','中美博弈','全球政策'];
function render(){
 const page=document.querySelector('.page[data-page-view="global"]'); if(!page||typeof data==='undefined')return;
 let panel=document.getElementById('globalSectorPanel'); if(!panel){panel=document.createElement('section');panel.id='globalSectorPanel';panel.className='panel';const matrix=page.querySelector('.matrix-panel');matrix?matrix.before(panel):page.appendChild(panel)}
 const items=data.filter(x=>x.region==='global');
 const counts=cats.map(c=>[c,items.filter(x=>(x.cat||x.category)===c).length]).filter(x=>x[1]>0).sort((a,b)=>b[1]-a[1]).slice(0,8);
 const top=items.slice().sort((a,b)=>(b.importance_score||0)-(a.importance_score||0)).slice(0,8);
 panel.innerHTML=`<div class="panel-title row"><span>🌐 全球政策板块</span><span class="sub">当前工作集 · ${items.length} 条</span></div><div class="direction-grid">${counts.map(x=>`<div class="direction"><h3>${esc(x[0])}</h3><div><span>情报数</span><i style="width:${Math.min(100,x[1]*10)}%"></i><small>${x[1]}</small></div></div>`).join('')||'<div class="item">暂无全球板块数据。</div>'}</div><div class="panel-title" style="margin-top:16px">全球重点情报 · 按重要度</div><div class="global-sector-feed">${top.map(x=>`<article class="item"><span class="badge ${esc(x.risk||'低')}">${esc(x.importance_level||x.risk||'C')}</span><h3>${x.url?`<a href="${x.url}" target="_blank" rel="noopener">${esc(x.titleZh||x.title)}</a>`:esc(x.titleZh||x.title)}</h3><div class="meta">${esc(x.cat||x.category||'全球政策')} · ${esc(x.sourceTier||x.source||'')} · ${esc(x.time||'')}</div></article>`).join('')||'<div class="item">暂无全球重点情报。</div>'}</div>`;
}
setTimeout(render,2200);setInterval(render,30000);window.addEventListener('load',render);
})();
