(()=>{
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const title=n=>n.titleZh||n.title||'';
const rank=a=>a.slice().sort((x,y)=>(y.importance_score||0)-(x.importance_score||0));
const grade=n=>n.importance_level==='S'?'s':n.importance_level==='A'?'a':'b';
function render(){
 if(typeof data==='undefined')return;
 const make=a=>a.map(n=>`<article class="policy-item"><span class="grade ${grade(n)}">${esc(n.importance_level||'B')}</span><small>${esc(n.time||'')}</small><h4>${n.url?`<a href="${n.url}" target="_blank" rel="noopener">${esc(title(n))}</a>`:esc(title(n))}</h4><p>${esc(n.cat||'')} · ${esc(n.sourceOrg||n.source||'')} · 重要度 ${n.importance_score||0}</p><span class="policy-stars">${'★'.repeat(n.importance_level==='S'?5:n.importance_level==='A'?4:3)}</span></article>`).join('')||'<div class="item">暂无重点信息。</div>';
 if($('homeChinaTop'))$('homeChinaTop').innerHTML=make(rank(data.filter(n=>n.region==='china')).slice(0,5));
 if($('homeUsTop'))$('homeUsTop').innerHTML=make(rank(data.filter(n=>n.region==='us')).slice(0,5));
 const focus=rank(data).filter(n=>(n.importance_score||0)>=55).slice(0,8);
 if($('todayFocus'))$('todayFocus').innerHTML=focus.map(n=>`<article class="focus-item"><span class="badge ${n.risk}">${esc(n.importance_level||'B')} · ${esc(n.risk||'')}</span><h3>${n.url?`<a href="${n.url}" target="_blank" rel="noopener">${esc(title(n))}</a>`:esc(title(n))}</h3><p>${esc(n.cat||'')} · ${esc(n.region||'')} · ${esc(n.sourceOrg||n.source||'')} · ${esc(n.importance_reason||'综合影响评估')}</p></article>`).join('')||'<div class="item">当前没有达到重要度阈值的重点事项。</div>';
 const f=typeof filter==='function'?filter():data, feed=$('feed');
 if(feed)feed.innerHTML=f.slice().sort((a,b)=>(b.importance_score||0)-(a.importance_score||0)).slice(0,100).map(n=>`<article class="item"><span class="badge ${n.risk}">${esc(n.importance_level||'B')} · ${esc(n.risk||'')}</span><h3>${n.url?`<a href="${n.url}" target="_blank" rel="noopener">${esc(title(n))}</a>`:esc(title(n))}</h3><div class="meta">重要度 ${n.importance_score||0} · ${esc(n.sourceTier||'其他媒体')} · ${esc(n.sourceOrg||n.source||'')} · ${esc(n.time||'')} · ${esc(n.cat||'')} · ${esc(n.region||'')}</div><div class="meta">${esc(n.importance_reason||'')}</div></article>`).join('')||'<div class="item">暂无符合条件的情报</div>';
 renderEvents();
}
function renderEvents(){const els=[$('dataEvents'),$('events')].filter(Boolean);if(!els.length)return;const groups={};data.forEach(n=>{const k=n.event_group||'宏观政策';(groups[k]??=[]).push(n)});const html=Object.entries(groups).sort((a,b)=>Math.max(...b[1].map(x=>x.importance_score||0),0)-Math.max(...a[1].map(x=>x.importance_score||0),0)).slice(0,8).map(([k,a])=>{const top=rank(a).slice(0,8);return `<article class="event"><h3>${esc(k)}</h3><p>${a.length} 条相关情报 · 最高重要度 ${top[0]?.importance_score||0} · ${top[0]?.importance_level||'B'}</p><div class="bar"><i style="width:${Math.min(100,top[0]?.importance_score||0)}%"></i></div><div class="event-list">${top.map(n=>`<div class="event-news"><a href="${n.url||'#'}" target="_blank" rel="noopener">${esc(title(n))}</a><small>${esc(n.time||'')} · ${esc(n.sourceOrg||n.source||'')} · ${esc(n.risk||'')}</small></div>`).join('')}</div></article>`}).join('')||'<div class="event">暂无事件。</div>';els.forEach(e=>e.innerHTML=html)}
setInterval(render,2000);setTimeout(render,800);
})();
