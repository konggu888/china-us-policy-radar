async function loadPolicyRadar(){
  try{
    const r=await fetch('data/policy_radar.json?'+Date.now(),{cache:'no-store'}); if(!r.ok)return;
    const d=await r.json(); const host=document.getElementById('policyRadar'); if(!host)return;
    host.innerHTML=`<section class="policy-head"><div><h2>🇨🇳 中国政策驾驶舱</h2><p>政策原文 → 支持工具 → 企业/行业行动 → 商品/价格 → 海关/统计 → 执行验证</p></div><small>更新：${escPR(d.updated||'')}</small></section>
    <div class="policy-grid">
      <div class="policy-card"><h3>政策源矩阵</h3><div class="agency-grid">${(d.source_matrix||[]).map(x=>`<div><b>${escPR(x.agency)}</b><small>${escPR(x.focus)}</small></div>`).join('')}</div></div>
      <div class="policy-card"><h3>政策语言变化雷达</h3><div class="language-list">${(d.language_radar||[]).map(x=>`<div><span>${escPR(x.keyword)}</span><b>${x.count}</b><em>${escPR(x.signal)}</em><small>近期 ${x.recent}</small></div>`).join('')}</div><p class="note">关键词频次用于发现方向变化，不代表政策意图。</p></div>
      <div class="policy-card"><h3>政策领域热度</h3><div class="area-list">${(d.policy_areas||[]).slice(0,8).map(x=>`<div><span>${escPR(x.name)}</span><i style="width:${Math.min(100,x.signals*8)}%"></i><b>${x.signals}</b><small>高风险 ${x.high_risk}</small></div>`).join('')}</div></div>
      <div class="policy-card chain"><h3>政策 → 现实验证链</h3><div class="chain-row">${(d.policy_chain?.steps||[]).map((x,i)=>`<div><strong>${i+1}</strong><span>${escPR(x)}</span><small>${escPR(d.policy_chain.status?.[i]||'待观察')}</small></div>`).join('')}</div><p class="note">${escPR(d.policy_chain?.rule||'')}</p></div>
    </div>
    <div class="policy-card policy-feed"><h3>重点政策情报</h3>${(d.policy_items||[]).slice(0,12).map(x=>`<article><span class="badge ${escPR(x.risk)}">${escPR(x.risk)}</span><h3>${x.url?`<a href="${x.url}" target="_blank" rel="noopener">${escPR(x.title)}</a>`:escPR(x.title)}</h3><p>${escPR(x.agency)} · ${escPR(x.category)} · ${escPR(x.date)} · ${escPR(x.verification)}</p><div><b>影响领域：</b>${escPR((x.impact_industry||[]).join('、'))}</div><div><b>短期：</b>${escPR(x.short_term)} <b>中长期：</b>${escPR(x.long_term)}</div><div><b>继续观察：</b>${escPR((x.watch_data||[]).join('、'))}</div></article>`).join('')||'<p>等待自动采集。</p>'}</div>`;
  }catch(e){}
}
function escPR(s=''){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
loadPolicyRadar();setInterval(loadPolicyRadar,10*60*1000);