(function(){
const SUPABASE_URL='https://ctiebkgsfmimedkoiapw.supabase.co';
const SUPABASE_KEY='sb_publishable_IcY5asvrEzEQSTCQB3XyCQ_GE1nuUje';
let sb=null;
function authEsc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function authLoad(){
  const tag=document.createElement('script');
  tag.src='https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.57.0/dist/umd/supabase.min.js';
  tag.onload=()=>{ sb=window.supabase.createClient(SUPABASE_URL,SUPABASE_KEY); if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',initAuth,{once:true}); else initAuth(); };
  tag.onerror=()=>console.warn('Supabase client failed to load');
  document.head.appendChild(tag);
}
function authPanel(){
  if(!document.getElementById('accountPanel')){
  const p=document.createElement('section'); p.id='accountPanel'; p.className='panel';
  p.innerHTML='<div class="title">👤 账号与云端同步</div><div id="authBox"><div class="controls"><label>账号（邮箱格式，仅作为登录名）<input id="authEmail" type="email" autocomplete="username" placeholder="你的账号邮箱"></label><label>密码<input id="authPassword" type="password" autocomplete="current-password" placeholder="至少 6 位"></label></div><div style="margin-top:10px"><button id="authLogin" type="button">登录</button> <button id="authSignup" type="button">注册</button></div><div id="authStatus" class="status">注册后直接使用账号和密码登录；不发送验证邮件。</div></div>';
  document.querySelector('header.hero').after(p);
  }
  const loginBtn=document.getElementById('authLogin');
  const signupBtn=document.getElementById('authSignup');
  if(loginBtn)loginBtn.onclick=login;
  if(signupBtn)signupBtn.onclick=signup;
}
function msg(t){const e=document.getElementById('authStatus');if(e)e.textContent=t;}
function bindNativeAuthButtons(){
 const l=document.getElementById('authLogin'),s=document.getElementById('authSignup');
 if(l)l.onclick=login;
 if(s)s.onclick=signup;
}
async function nativeAuthRequest(path,body){
 const res=await fetch(SUPABASE_URL+path,{method:'POST',headers:{'Content-Type':'application/json','apikey':SUPABASE_KEY},body:JSON.stringify(body)});
 let data=null; try{data=await res.json();}catch(_){data={};}
 if(!res.ok) throw new Error(data?.msg||data?.message||data?.error_description||'Supabase 请求失败（HTTP '+res.status+'）');
 return data;
}
async function login(){
 const btn=document.getElementById('authLogin');
 if(btn?.dataset.busy==='1')return;
 const email=document.getElementById('authEmail')?.value.trim()||'', password=document.getElementById('authPassword')?.value||'';
 if(!email||!password)return msg('请输入邮箱和密码。');
 if(btn)btn.dataset.busy='1'; msg('正在登录，请稍候……');
 try{
   let data;
   if(sb){
     const r=await sb.auth.signInWithPassword({email,password});
     if(r.error)throw new Error(r.error.message);
     data={session:r.data?.session,user:r.data?.user};
   }else{
     data=await nativeAuthRequest('/auth/v1/token?grant_type=password',{email,password});
     if(data?.access_token&&data?.refresh_token){localStorage.setItem('scenario_auth_fallback',JSON.stringify({access_token:data.access_token,refresh_token:data.refresh_token}));}
   }
   if(!data?.session&&!data?.access_token){msg('登录未建立会话，请检查账号、密码及 Supabase Email 登录配置。');return;}
   msg('登录成功，正在同步历史推演……');
   if(sb&&data?.access_token&&data?.refresh_token)await sb.auth.setSession({access_token:data.access_token,refresh_token:data.refresh_token});
   if(sb){await cloudPull();patchSandboxHooks();}
   else msg('登录成功；云端同步组件正在加载，请刷新页面后即可继续同步。');
 }catch(e){msg('登录失败：'+(e?.message||'请检查网络后重试。'));}
 finally{if(btn)btn.dataset.busy='0';}
}
async function signup(){
 const btn=document.getElementById('authSignup'); if(btn?.dataset.busy==='1')return;
 const email=document.getElementById('authEmail')?.value.trim()||'', password=document.getElementById('authPassword')?.value||'';
 if(!email)return msg('请输入账号。'); if(password.length<6)return msg('注册需要至少 6 位密码。');
 if(btn)btn.dataset.busy='1'; msg('正在创建账号，请稍候……');
 try{
   let data;
   if(sb){const r=await sb.auth.signUp({email,password});if(r.error)throw new Error(r.error.message);data={session:r.data?.session,user:r.data?.user};}
   else data=await nativeAuthRequest('/auth/v1/signup',{email,password});
   if(data?.access_token&&data?.refresh_token)localStorage.setItem('scenario_auth_fallback',JSON.stringify({access_token:data.access_token,refresh_token:data.refresh_token}));
   if(data?.session||data?.access_token){msg('注册成功，已直接登录。'); if(sb&&data?.access_token)await sb.auth.setSession({access_token:data.access_token,refresh_token:data.refresh_token}); if(sb)await cloudPull();}
   else msg('账号已创建，但 Supabase 仍要求邮箱确认。请关闭 Confirm email 后再注册。');
 }catch(e){msg('注册失败：'+(e?.message||'请检查网络后重试。'));}
 finally{if(btn)btn.dataset.busy='0';}
}
async function cloudPull(){
 const {data:{user}}=await currentUser(); if(!user)return;
 const {data,error}=await sb.from('scenario_tasks').select('id,event,goal,horizon,mode,created_at,updated_at,last_run_at,payload').eq('user_id',user.id).order('updated_at',{ascending:false}).limit(50);
 if(error){msg('云端同步读取失败：'+error.message);return;}
 const incoming=(data||[]).map(r=>({id:r.id,event:r.event,goal:r.goal,horizon:r.horizon,mode:r.mode,createdAt:r.created_at,updatedAt:r.updated_at,lastRunAt:r.last_run_at,...(r.payload||{})}));
 const map=new Map(loadTaskArchive().map(t=>[t.id,t])); incoming.forEach(t=>map.set(t.id,t));
 saveTaskArchive(Array.from(map.values()).sort((a,b)=>String(b.updatedAt||'').localeCompare(String(a.updatedAt||''))));
 renderTaskArchive(); msg('已登录：历史推演已与云端同步。');
}
window.syncTasksFromServer=cloudPull;
window.syncTaskToServer=async function(task){
 const {data:{user}}=await currentUser(); if(!user)return;
 const payload={...task}; delete payload.id; delete payload.event; delete payload.goal; delete payload.horizon; delete payload.mode; delete payload.createdAt; delete payload.updatedAt; delete payload.lastRunAt;
 const row={id:String(task.id),user_id:user.id,event:String(task.event||''),goal:task.goal||null,horizon:task.horizon||null,mode:task.mode||null,created_at:task.createdAt||new Date().toISOString(),updated_at:task.updatedAt||new Date().toISOString(),last_run_at:task.lastRunAt||null,payload};
 const {error}=await sb.from('scenario_tasks').upsert(row,{onConflict:'id'});
 if(error)msg('云端保存失败：'+error.message);
};
window.saveScenarioRun=async function(task,scenario){
 const {data:{user}}=await currentUser(); if(!user||!scenario)return;
 const radar=window.__scenarioState||{};
 const registry=(radar.scenarioSnapshot?.evidenceRegistry||[]).filter(x=>(scenario.evidenceDrivers||[]).some(d=>String(d.id||'')===String(x.id||''))).slice(0,30);
 const payload={scenario,radarContext:{generatedAt:radar.generated_at||null,state:radar.state||{},events:(radar.events||[]).slice(0,20),market:(radar.state?.finance?.market||[]).slice(0,20)},evidenceRegistry:registry,validation:{timeWindowValidation:(radar.scenarioSnapshot?.timeWindowValidation||[]).filter(x=>String(x.scenarioCode||'')===String(scenario.code||'')),crossRunValidation:(radar.scenarioSnapshot?.crossRunValidation||[]).filter(x=>String(x.scenarioCode||'')===String(scenario.code||'')),historicalMarketWindows:(radar.scenarioSnapshot?.historicalMarketWindows||[]).filter(x=>(scenario.evidenceDrivers||[]).some(d=>String(d.id||'')===String(x.eventId||''))).slice(0,20)},recordedAt:new Date().toISOString()};
 const row={task_id:String(task.id),user_id:user.id,status:'RECORDED',scenario_code:scenario.code||null,activation_state:scenario.activationState||null,trigger_score:scenario.triggerScore??null,confidence:scenario.confidence||null,evidence_count:Array.isArray(scenario.evidenceDrivers)?scenario.evidenceDrivers.length:null,payload};
 const {data:insertedRun,error}=await sb.from('scenario_task_runs').insert(row).select('id,observed_at').single();
 if(error){console.warn('scenario run save failed',error.message);return;}
 const runAt=insertedRun?.observed_at||payload.recordedAt;
 const taskPayload={...task};
 delete taskPayload.id; delete taskPayload.event; delete taskPayload.goal; delete taskPayload.horizon; delete taskPayload.mode; delete taskPayload.createdAt; delete taskPayload.updatedAt; delete taskPayload.lastRunAt;
 const taskRow={id:String(task.id),user_id:user.id,event:String(task.event||''),goal:task.goal||null,horizon:task.horizon||null,mode:task.mode||null,created_at:task.createdAt||new Date().toISOString(),updated_at:new Date().toISOString(),last_run_at:runAt,payload:taskPayload};
 const {error:taskError}=await sb.from('scenario_tasks').upsert(taskRow,{onConflict:'id'});
 if(taskError)console.warn('scenario task last-run update failed',taskError.message);
};
async function buildTriggerFeedback(taskId,currentRun,previousRun){
 const {data:{user}}=await currentUser();
 if(!user||!currentRun)return;
 const sc=currentRun.payload?.scenario||{};
 const currentDrivers=(sc.evidenceDrivers||[]).filter(d=>d.kind==='EVENT');
 if(!currentDrivers.length)return;
 const registry=currentRun.payload?.evidenceRegistry||[];
 const validation=currentRun.payload?.validation||{};
 const crossRun=validation.crossRunValidation||[];
 const rowsByTrigger=new Map();
 for(const d of currentDrivers){
   const trigger=String(d.category||d.role||'UNKNOWN_TRIGGER');
   const key=String(d.id||'');
   const r=registry.find(x=>String(x.dedupeKey||'')===key || String(x.id||'')===key || String(x.eventId||'')===key);
   const cross=crossRun.find(x=>String(x.driverId||'')===key);
   const repeated=Number(r?.observationCount||0)>1 || Number(r?.independentSourceCount||0)>1 || !!r?.followupObserved;
   const multiRun=Number(cross?.runObservationCount||0)>=2;
   const followup=Number(cross?.followupRunCount||0)>0 || !!r?.followupObserved;
   const observedMarket=Number(cross?.marketObservedRunCount||0);
   const evidenceCount=(repeated?1:0)+(multiRun?1:0)+(followup?1:0);
   const support=evidenceCount>0;
   const counterRunCount=Number(cross?.counterRunCount||0);
   const counterSignalCount=Number(cross?.counterSignalCount||0);
   const counterStrength=Number(cross?.counterSignalStrength||0);
   const counterObserved=counterRunCount>0||counterSignalCount>0;
   const weakened=counterObserved && counterRunCount>=2 && counterStrength>=1.5 && !followup;
   const outcome=weakened?'WEAKENED':(support?'SUPPORTED':'UNRESOLVED');
   const bucket=rowsByTrigger.get(trigger)||{outcomes:[],evidence:0,followup:0,market:0,counterRuns:0,counterCount:0,counterStrength:0};
   bucket.outcomes.push(outcome); bucket.evidence+=evidenceCount; bucket.followup+=followup?1:0; bucket.market+=observedMarket; bucket.counterRuns+=counterRunCount; bucket.counterCount+=counterSignalCount; bucket.counterStrength+=counterStrength; rowsByTrigger.set(trigger,bucket);
 }
 const {data:existing}=await sb.from('scenario_trigger_feedback').select('trigger,calibration_factor,sample_size,status').eq('user_id',user.id).eq('task_id',String(taskId)).order('created_at',{ascending:false}).limit(100);
 const latest=new Map((existing||[]).map(x=>[x.trigger,x]));
 const rows=[...rowsByTrigger.entries()].map(([trigger,b])=>{
   const supported=b.outcomes.filter(x=>x==='SUPPORTED').length;
   const weakened=b.outcomes.filter(x=>x==='WEAKENED').length;
   const outcome=supported>weakened?'SUPPORTED':(weakened>supported?'WEAKENED':'UNRESOLVED');
   const old=latest.get(trigger), n=Number(old?.sample_size||0)+1, prior=Number(old?.calibration_factor||1);
   const raw=outcome==='SUPPORTED'?1.03:(outcome==='WEAKENED'?0.97:1);
   const proposed=Math.max(0.8,Math.min(1.2,prior*raw));
   const frozen=n<3||Math.abs(proposed-prior)>0.10;
   const applied=frozen?prior:proposed;
   return {user_id:user.id,task_id:String(taskId),trigger,observed_run_id:currentRun.id,prior_run_id:previousRun?.id||null,outcome,evidence_count:b.evidence,followup_count:b.followup,market_deviation_count:b.market,sample_size:n,calibration_factor:Number(applied.toFixed(3)),status:n<3?'EARLY_SAMPLE':(frozen?'FROZEN':'CALIBRATED'),payload:{priorFactor:prior,proposedFactor:Number(proposed.toFixed(3)),appliedFactor:Number(applied.toFixed(3)),method:'基于跨运行正向后续证据、反向反证信号、多源重复观察与真实历史市场窗口；不再使用相邻运行触发分数变化作为支持/减弱依据。',counterSignalRunCount:b.counterRuns,counterSignalCount:b.counterCount,counterSignalStrength:Number(b.counterStrength.toFixed(3)),outcomes:b.outcomes,crossRunValidation:crossRun.filter(x=>String(x.driverId||'')===String(currentDrivers.find(d=>String(d.category||d.role||'UNKNOWN_TRIGGER')===trigger)?.id||''))}};
 });
 if(!rows.length)return;
 const {data:ins,error}=await sb.from('scenario_trigger_feedback').insert(rows).select('id,trigger,calibration_factor,status,sample_size');
 if(error||!ins)return;
 for(const x of ins){
   const src=rows.find(y=>y.trigger===x.trigger);
   await sb.from('scenario_calibration_audit').insert({user_id:user.id,task_id:String(taskId),trigger:x.trigger,feedback_id:x.id,prior_factor:Number(src?.payload?.priorFactor||1),proposed_factor:Number(src?.payload?.proposedFactor||1),applied_factor:Number(x.calibration_factor||1),delta:Number((Number(x.calibration_factor||1)-Number(src?.payload?.priorFactor||1)).toFixed(3)),status:x.status==='FROZEN'?'FROZEN':(x.status==='EARLY_SAMPLE'?'EARLY_SAMPLE':'APPLIED'),sample_size:x.sample_size,reason:src?.payload?.method||'跨运行历史后续证据校准'});
 }
}
async function renderEffectiveTriggerWeights(sc){
 const box=document.getElementById('effectiveTriggerWeights'); if(!box||!sb||!sc)return;
 const {data:{user}}=await currentUser();
 const globalRows=window.__triggerCalibration||[];
 const globalMap=new Map(globalRows.map(x=>[String(x.trigger),x]));
 const taskId=(sc?.taskId||window.__activeScenarioTaskId||loadTaskArchive()[0]?.id||'');
 let userRows=[];
 if(user&&taskId){
   const {data}=await sb.from('scenario_trigger_feedback').select('trigger,calibration_factor,sample_size,status').eq('task_id',String(taskId)).order('created_at',{ascending:false}).limit(100);
   userRows=data||[];
 }
 const userMap=new Map(); userRows.forEach(x=>{if(!userMap.has(String(x.trigger)))userMap.set(String(x.trigger),x);});
 const drivers=[...(sc.evidenceDrivers||[]).filter(x=>x.kind==='EVENT')];
 const triggers=[...new Set([...drivers.map(d=>String(d.category||d.role||'UNKNOWN_TRIGGER')),...(sc.triggerEvidence||[]).map(x=>String(x))])];
 const rows=triggers.map(t=>{
   const g=globalMap.get(t),u=userMap.get(t);
   const base=1, gf=(g?.status==='CALIBRATED'?Number(g.calibrationWeight||1):1), uf=(u?.status==='CALIBRATED'?Number(u.calibration_factor||1):1);
   const eff=Math.max(.8,Math.min(1.2,gf*uf));
   return {t,gf,uf,eff,gs:g?.status||'无全局样本',us:u?.status||'无账户样本',n:u?.sample_size||0,source:g?.historicalSignalRate??null};
 });
 box.innerHTML=rows.length?'<div class="card"><b>当前触发器有效权重</b><div class="mini muted">基础权重固定为 1.00；全局历史校准与本账号历史反馈分别展示。有效权重只作为监测敏感度参考，不直接代表发生概率。</div>'+rows.map(r=>'<div class="mini" style="margin-top:7px"><b>'+authEsc(r.t)+'</b> · 基础 1.000 → 全局 '+r.gf.toFixed(3)+' → 账户 '+r.uf.toFixed(3)+' → <b>当前 '+r.eff.toFixed(3)+'</b> · 全局 '+authEsc(r.gs)+' · 账户 '+authEsc(r.us)+(r.n?' · 账户样本 '+r.n:'')+'</div>').join('')+'</div>':'<div class="card muted">当前情景暂无可映射的事件触发器。</div>';
}
async function renderUserTriggerCalibration(taskId){
 const box=document.getElementById('triggerCalibrationList'); if(!box||!taskId||!sb)return;
 const {data,error}=await sb.from('scenario_trigger_feedback').select('trigger,outcome,evidence_count,followup_count,market_deviation_count,sample_size,calibration_factor,status,created_at').eq('task_id',String(taskId)).order('created_at',{ascending:false}).limit(80);
 if(error){box.innerHTML='<div class="card muted">历史校准读取失败。</div>';return;}
 const latest=new Map(); (data||[]).forEach(r=>{if(!latest.has(r.trigger))latest.set(r.trigger,r);});
 const rows=[...latest.values()];
 box.innerHTML=rows.length?rows.map(r=>'<article class="card"><b>'+authEsc(r.trigger)+'</b><div class="muted mini">样本 '+r.sample_size+' · '+authEsc(r.status)+' · 校准因子 '+Number(r.calibration_factor).toFixed(3)+'</div><div class="mini">最近结果：'+authEsc(r.outcome)+' · 新增证据 '+r.evidence_count+' · 后续证据 '+r.followup_count+' · 市场偏离 '+r.market_deviation_count+' · 反证信号将从跨运行历史累计后参与监控校准</div><div class="mini muted">描述性历史反馈，不是发生概率、胜率或因果估计。</div></article>').join(''):'<div class="card muted">形成历史样本后，这里会逐步出现触发器反馈。</div>';
}
function renderAuthState(user){
 const box=document.getElementById('authBox'); if(!box)return;
 if(user) box.innerHTML='<div class="status">已登录：<b>'+authEsc(user.email||'账号')+'</b>。历史推演自动云端保存。 <button id="authLogout">退出登录</button></div><div class="mini muted">账号跨设备同步，不再需要保存同步密钥。</div>';
 else authPanel();
 const lo=document.getElementById('authLogout'); if(lo)lo.onclick=async()=>{await sb.auth.signOut();msg('已退出登录。')};
}
async function renderTaskOverview(taskId,rows){
 const box=document.getElementById('taskOverview');
 if(!box||!taskId||!sb)return;
 const all=rows||[];
 if(!all.length){box.innerHTML='<div class="card muted">完成一次推演后，这里会形成任务级总览。</div>';return;}
 const latest=all[0], prev=all[1];
 const lp=latest.payload||{}, sc=lp.scenario||{}, validation=lp.validation||{};
 const drivers=(sc.evidenceDrivers||[]).filter(x=>x.kind==='EVENT');
 const registry=lp.evidenceRegistry||[];
 const observedWindows=[...new Set((validation.timeWindowValidation||[]).flatMap(x=>(x.details||[]).filter(d=>d.status==='OBSERVED').map(d=>d.window)))];
 const missingWindows=[...new Set((validation.timeWindowValidation||[]).flatMap(x=>(x.details||[]).filter(d=>d.status==='MISSING').map(d=>d.window)))];
 const market=(validation.historicalMarketWindows||[]);
 const marketObserved=market.filter(x=>x.status==='OBSERVED').length;
 const marketMissing=market.filter(x=>x.status==='MISSING').length;
 const counters=(sc.counterSignalAnalysis?.signals||[]);
 const cross=validation.crossRunValidation||[];
 const supported=drivers.filter(d=>{const r=registry.find(x=>String(x.id||x.dedupeKey||x.eventId||'')===String(d.id||''));return Number(r?.observationCount||0)>1||Number(r?.independentSourceCount||0)>1||!!r?.followupObserved;}).length;
 const unresolved=Math.max(0,drivers.length-supported);
 const scoreDelta=prev==null?null:Number(latest.trigger_score||0)-Number(prev.trigger_score||0);
 const state=String(latest.activation_state||sc.activationState||'WATCH');
 const statusText=state==='ACTIVE'?'当前触发条件较充分，继续做后续验证':state==='WATCH'?'保持观察，继续等待触发与反证':'当前情景状态：'+state;
 const tile=(title,value,sub)=>'<div class="card"><b>'+authEsc(title)+'</b><div style="font-size:20px;margin-top:5px">'+authEsc(String(value))+'</div><div class="muted mini">'+authEsc(sub||'')+'</div></div>';
 box.innerHTML='<div class="card"><div class="scenario-summary-head"><div><b>🧭 任务级总览</b><div class="muted mini">基于最近一次真实雷达快照；不把后来信息倒灌到过去。</div></div><span class="tag">'+authEsc(state)+'</span></div><p>'+authEsc(statusText)+'</p><div class="scenario-summary-grid">'+
 tile('当前情景',latest.scenario_code||sc.code||'未标注','触发分数 '+Number(latest.trigger_score||0).toFixed(2)+(scoreDelta==null?'':' · 较上次 '+(scoreDelta>=0?'+':'')+scoreDelta.toFixed(2)))+
 tile('直接触发器',drivers.length,supported+' 个已有重复/后续观察 · '+unresolved+' 个仍待验证')+
 tile('时间窗口',observedWindows.length,missingWindows.length+' 个窗口暂缺历史快照')+
 tile('市场验证',marketObserved,marketMissing+' 个市场窗口缺失')+
 tile('反证信号',counters.length,'跨运行记录 '+Number(cross.reduce((n,x)=>n+Number(x.counterSignalCount||0),0))+' 个')+
 tile('历史运行',all.length,'最近运行 '+(latest.observed_at||'未知'))+
 '</div><div class="mini" style="margin-top:8px"><b>已验证条件：</b>'+authEsc(supported?drivers.slice(0,supported).map(x=>x.title||x.id).join('；'):'目前没有足够的重复/后续观察')+'</div><div class="mini" style="margin-top:6px"><b>下一观察重点：</b>核验新增正式政策文本、后续事件、时间窗口、市场快照与反证；出现关键反证时重新建模。</div></div>';
}
async function renderTaskRuns(taskId){
 const box=document.getElementById('taskRunsList'); if(!box||!taskId||!sb)return;
 const {data,error}=await sb.from('scenario_task_runs').select('id,observed_at,status,scenario_code,activation_state,trigger_score,confidence,evidence_count,payload').eq('task_id',String(taskId)).order('observed_at',{ascending:false}).limit(30);
 if(error){box.innerHTML='<div class="card muted">运行历史读取失败。</div>';return;}
 const rows=data||[];
 await renderTaskOverview(taskId,rows);
 box.innerHTML=rows.length?rows.map((r,i)=>{
   const p=r.payload||{}, sc=p.scenario||{};
   const ctx=p.radarContext||{};
   const ev=(sc.evidenceDrivers||[]).filter(x=>x.kind==='EVENT').slice(0,4).map(x=>authEsc(x.title||x.id)).join('；');
   const prev=rows[i+1]||null, pp=prev?.payload?.scenario||{};
   const scoreDelta=prev?Number(r.trigger_score||0)-Number(prev.trigger_score||0):null;
   const confChange=prev&&pp.confidence&&sc.confidence&&pp.confidence!==sc.confidence?'置信度 '+authEsc(pp.confidence)+' → '+authEsc(sc.confidence):'';
   const stateChange=prev&&pp.activationState&&sc.activationState&&pp.activationState!==sc.activationState?'状态 '+authEsc(pp.activationState)+' → '+authEsc(sc.activationState):'';
   const currentIds=new Set((sc.evidenceDrivers||[]).filter(x=>x.kind==='EVENT').map(x=>String(x.id)));
   const previousIds=new Set((pp.evidenceDrivers||[]).filter(x=>x.kind==='EVENT').map(x=>String(x.id)));
   const added=[...currentIds].filter(x=>!previousIds.has(x)).length;
   const removed=[...previousIds].filter(x=>!currentIds.has(x)).length;
   const validation=p.validation||{};
   const tw=(validation.timeWindowValidation||[]).filter(x=>x.scenarioCode===r.scenario_code);
   const mw=(validation.historicalMarketWindows||[]).filter(x=>x.eventId&&new Set((sc.evidenceDrivers||[]).map(d=>String(d.id))).has(String(x.eventId)));
   const counters=(sc.counterSignalAnalysis?.signals||[]).length;
   const observedWindows=[...new Set(tw.flatMap(x=>(x.details||[]).filter(d=>d.status==='OBSERVED').map(d=>d.window)))];
   const missingWindows=[...new Set(tw.flatMap(x=>(x.details||[]).filter(d=>d.status==='MISSING').map(d=>d.window)))];
   const marketObserved=mw.filter(x=>x.status==='OBSERVED').length;
   const marketMissing=mw.filter(x=>x.status==='MISSING').length;
   const statusLine='时间窗口 '+observedWindows.length+' 个已观察'+(missingWindows.length?' · '+missingWindows.length+' 个尚无历史快照':'')+'；市场验证 '+marketObserved+' 个已观察'+(marketMissing?' · '+marketMissing+' 个缺失':'')+'；反证信号 '+counters+' 个';
   const feedbackText=prev?'触发分数 '+(scoreDelta>=0?'+':'')+scoreDelta.toFixed(2)+'；新增证据 '+added+'；移出证据 '+removed+(stateChange?'；'+stateChange:'')+(confChange?'；'+confChange:''):'这是该任务的首次记录，尚未形成跨运行反馈。';
   const feedbackHint=prev?'下一轮重点：复核新增/移出证据、后续窗口、市场观察和反证。':'下一轮开始后，系统会把本次快照与后续现实观察进行对照。';
   return '<article class="card"><b>#'+(rows.length-i)+' · '+authEsc(r.scenario_code||'未标注')+' · '+authEsc(r.activation_state||'WATCH')+' · '+Number(r.trigger_score||0).toFixed(2)+'</b><div class="muted mini">运行时间：'+authEsc(r.observed_at||'')+' · 置信度：'+authEsc(r.confidence||'—')+' · 证据：'+Number(r.evidence_count||0)+'</div><div class="mini">当时雷达：'+authEsc(ctx.generatedAt||'未知')+'</div><div class="mini">直接事件：'+authEsc(ev||'暂无')+'</div><div class="mini">验证状态：'+authEsc(statusLine)+'</div><div class="mini">运行反馈：'+feedbackText+'</div><div class="mini">'+authEsc(feedbackHint)+'</div><div class="mini muted">记录包含当时态势、事件、市场与证据快照；变化只做历史对照，不表示因果关系或发生概率。</div></article>';
 }).join(''):'<div class="card muted">这个任务还没有服务器运行记录。完成一次推演后会自动留下审计记录。</div>';
}
function ensureTaskRunsPanel(){
 if(document.getElementById('taskRunsPanel'))return;
 const anchor=document.getElementById('taskArchive');
 if(!anchor)return;
 const p=document.createElement('section');p.id='taskRunsPanel';p.className='panel';
 p.innerHTML='<div class="title">🧭 任务级总览</div><div id="taskOverview" class="actions" style="margin-top:10px"><div class="card muted">选择或运行一个任务后生成。</div></div><div class="title" style="margin-top:14px">🧾 推演运行历史 · 第二阶段</div><div class="mini muted">每次运行保存当时的雷达时间、态势、关键事件、市场快照、剧本状态和证据驱动。这里记录历史事实，不把后来的信息倒灌回过去。</div><div id="taskRunsList" class="actions" style="margin-top:10px"><div class="card muted">选择或运行一个任务后加载。</div></div><div class="title" style="margin-top:14px">🧪 第三阶段 · 历史触发器校准</div><div class="mini muted">连续运行样本用于记录触发器在后续观察中被支持、减弱或仍无法确认；样本不足时不调整权重。</div><div id="triggerCalibrationList" class="actions" style="margin-top:10px"><div class="card muted">形成历史样本后显示。</div></div>';
 anchor.after(p);
}
function patchSandboxHooks(){
 if(window.__supabaseSandboxHooks)return;
 if(typeof window.archiveTask!=='function'||typeof window.renderTaskArchive!=='function'||typeof window.runScenarioTask!=='function'){setTimeout(patchSandboxHooks,100);return;}
 window.__supabaseSandboxHooks=true;
 const oldRender=window.renderTaskArchive;
 window.renderTaskArchive=function(){
   oldRender();
   const legacy=document.querySelector('#taskArchiveList button[onclick="setTaskApi()"]');
   if(legacy) legacy.remove();
   const hint=document.querySelector('#taskArchiveList .muted.mini');
   if(hint) hint.textContent='已登录账号后自动云端保存；无需同步密钥。';
 };
 const oldRenderScenario=window.renderSandboxScenario;
 if(typeof oldRenderScenario==='function'){
   window.renderSandboxScenario=function(sc,index){const result=oldRenderScenario(sc,index); setTimeout(()=>renderEffectiveTriggerWeights(sc),50); return result;};
 }
 const oldRun=window.runScenarioTask;
 window.runScenarioTask=function(task){
   const result=oldRun(task);
   setTimeout(async()=>{
     const sc=window.__selectedScenario;
     if(sc){
 await window.saveScenarioRun(task,sc);
 const {data:{user}}=await currentUser();
 if(user){
   const {data:runs}=await sb.from('scenario_task_runs').select('id,observed_at,trigger_score,payload').eq('task_id',String(task.id)).order('observed_at',{ascending:false}).limit(2);
   if(runs?.[0]){await buildTriggerFeedback(task.id,runs[0],runs?.[1]);}
 }
 await renderTaskRuns(task.id); await renderUserTriggerCalibration(task.id);
}
   },250);
   return result;
 };
 ensureTaskRunsPanel();
 window.renderTaskArchive();
}
function initAuth(){
 authPanel();
 bindNativeAuthButtons();
 const hash=location.hash||'';
 const search=location.search||'';
 

 sb.auth.onAuthStateChange(async(_event,session)=>{
   renderAuthState(session?.user||null);
   if(session?.user){await cloudPull();patchSandboxHooks();}
 });
 sb.auth.getSession().then(async({data:{session}})=>{renderAuthState(session?.user||null);if(session?.user){await cloudPull();patchSandboxHooks(); if(loadTaskArchive()[0]) await renderUserTriggerCalibration(loadTaskArchive()[0].id); msg('登录状态已确认，云端历史推演已同步。');}});
}
authLoad();
})();