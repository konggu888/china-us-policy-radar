(()=>{
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const zh=n=>n.titleZh||n.title||'';
function render(){
 if(typeof data==='undefined')return;
 const el=$('compareMain'); if(!el)return;
 const mk=(label,region,theme)=>{
   const a=data.filter(n=>n.region===region).slice().sort((x,y)=>(y.importance_score||0)-(x.importance_score||0)).slice(0,8);
   const parts=label.split(' '), flag=parts[0], title=parts.slice(1).join(' ');
   return `<article class="compare compare-signal ${theme}">
     <header class="compare-signal-head">
       <div class="compare-signal-title"><span class="compare-flag">${flag}</span><h3>${esc(title)}</h3></div>
       <span class="compare-signal-count">${a.length||'—'} 条</span>
     </header>
     <div class="compare-signal-sub">重点情报 · 按重要度排序</div>
     <div class="compare-news-list">
       ${a.map((n,i)=>`<a class="compare-news-item" href="${esc(n.url||'#')}" target="_blank" rel="noopener">
         <span class="compare-news-rank">${String(i+1).padStart(2,'0')}</span>
         <span class="compare-news-body">
           <strong>${esc(zh(n))}</strong>
           <span class="compare-news-meta"><b>${esc(n.importance_level||'B')}</b><em>${esc(n.cat||'未分类')}</em><span>重要度 ${n.importance_score||0}</span><span>${esc(n.sourceOrg||n.source||'')}</span></span>
         </span>
       </a>`).join('')||'<div class="compare-empty">暂无重点情报</div>'}
     </div>
   </article>`;
 };
 el.innerHTML=mk('🇨🇳 中国重点信号','china','compare-china')+mk('🇺🇸 美国重点信号','us','compare-us');
}
setTimeout(render,1200);setInterval(render,30000);
})();
