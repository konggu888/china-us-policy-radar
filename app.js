const demo=[
 {title:'示例：全球主要央行与利率路径变化',region:'global',cat:'金融经济',risk:'中',source:'待自动采集',time:'—',x:64,y:35},
 {title:'示例：中美贸易、科技与投资限制动态',region:'china',cat:'中美竞争',risk:'高',source:'待自动采集',time:'—',x:37,y:43},
 {title:'示例：印太地区军事与安全态势',region:'global',cat:'军事',risk:'高',source:'待自动采集',time:'—',x:72,y:61},
 {title:'示例：全球能源供应与运输风险',region:'global',cat:'能源安全',risk:'中',source:'待自动采集',time:'—',x:58,y:76}
];
let data=[];
async function load(){try{const r=await fetch('data/news.json?'+Date.now());data=await r.json()}catch(e){data=demo}render()}
function render(){const f=filter();document.getElementById('count').textContent=f.length+' 条';document.getElementById('updated').textContent='数据更新时间：'+(data[0]?.updated||'每日自动更新');
 const risks={critical:0,high:0,medium:0,low:0};data.forEach(n=>{if(n.risk==='极高')risks.critical++;else if(n.risk==='高')risks.high++;else if(n.risk==='中')risks.medium++;else risks.low++});
 document.getElementById('kpis').innerHTML=[[''+data.length,'今日情报'],[risks.critical,'极高风险'],[risks.high,'高风险'],[new Set(data.map(x=>x.country||x.region)).size,'重点区域']].map(x=>`<div class="kpi"><b>${x[0]}</b><span>${x[1]}</span></div>`).join('');
 document.getElementById('feed').innerHTML=f.slice(0,80).map(n=>`<article class="item"><span class="badge ${n.risk}">${n.risk}</span><h3>${n.url?`<a href="${n.url}" target="_blank" rel="noopener">${esc(n.title)}</a>`:esc(n.title)}</h3><div class="meta">${esc(n.source||'')} · ${esc(n.time||'')} · ${esc(n.cat||'')}</div></article>`).join('')||'<div class="item">暂无符合条件的情报</div>';
 document.getElementById('blips').innerHTML=f.slice(0,50).map(n=>`<i class="blip ${n.risk==='极高'?'critical':n.risk==='高'?'high':n.risk==='中'?'medium':'low'}" style="left:${n.x||50}%;top:${n.y||50}%"></i>`).join('');document.getElementById('hotspots').innerHTML=[...new Set(f.map(x=>x.cat))].map(x=>`<span class="tag">${esc(x)}</span>`).join('')}
function filter(){const r=document.getElementById('region').value,c=document.getElementById('category').value,k=document.getElementById('risk').value,q=document.getElementById('search').value.toLowerCase();return data.filter(n=>(r==='all'||n.region===r)&&(c==='all'||n.cat===c)&&(k==='all'||({critical:'极高',high:'高',medium:'中',low:'低'}[k]===n.risk))&&(!q||JSON.stringify(n).toLowerCase().includes(q)))}
function esc(s=''){return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
['region','category','risk','search'].forEach(id=>document.getElementById(id).addEventListener('input',render));load();
