(function(){
const SUPABASE_URL='https://ctiebkgsfmimedkoiapw.supabase.co';
const SUPABASE_KEY='sb_publishable_IcY5asvrEzEQSTCQB3XyCQ_GE1nuUje';
let sb=null;
function authLoad(){
  const tag=document.createElement('script');
  tag.src='https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.57.0/dist/umd/supabase.min.js';
  tag.onload=()=>{ sb=window.supabase.createClient(SUPABASE_URL,SUPABASE_KEY); if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',initAuth,{once:true}); else initAuth(); };
  tag.onerror=()=>console.warn('Supabase client failed to load');
  document.head.appendChild(tag);
}
function authPanel(){
  if(document.getElementById('accountPanel'))return;
  const p=document.createElement('section'); p.id='accountPanel'; p.className='panel';
  p.innerHTML='<div class="title">👤 账号与云端同步</div><div id="authBox"><div class="controls"><label>邮箱<input id="authEmail" type="email" autocomplete="email" placeholder="你的邮箱"></label><label>密码<input id="authPassword" type="password" autocomplete="current-password" placeholder="至少 6 位"></label></div><div style="margin-top:10px"><button id="authLogin">登录</button> <button id="authSignup">注册</button> <button id="authReset">忘记密码</button></div><div id="authStatus" class="status">登录后，历史推演会自动保存到你的账号；不再需要同步密钥。</div></div>';
  document.querySelector('header.hero').after(p);
  document.getElementById('authLogin').onclick=login;
  document.getElementById('authSignup').onclick=signup;
  document.getElementById('authReset').onclick=resetPassword;
}
function msg(t){const e=document.getElementById('authStatus');if(e)e.textContent=t;}
async function login(){
 const email=document.getElementById('authEmail').value.trim(), password=document.getElementById('authPassword').value;
 if(!email||!password)return msg('请输入邮箱和密码。');
 const {error}=await sb.auth.signInWithPassword({email,password});
 msg(error?('登录失败：'+error.message):'登录成功，正在同步历史推演……');
}
async function signup(){
 const email=document.getElementById('authEmail').value.trim(), password=document.getElementById('authPassword').value;
 if(!email||password.length<6)return msg('注册需要有效邮箱和至少 6 位密码。');
 const {data,error}=await sb.auth.signUp({email,password,options:{emailRedirectTo:location.origin+location.pathname}});
 if(error)return msg('注册失败：'+error.message);
 msg(data.session?'注册成功。':'注册成功，请先查收邮箱完成验证。');
}
async function resetPassword(){
 const email=document.getElementById('authEmail').value.trim();
 if(!email)return msg('请先输入邮箱。');
 const {error}=await sb.auth.resetPasswordForEmail(email,{redirectTo:location.href});
 msg(error?('发送失败：'+error.message):'密码重置邮件已发送，请查收邮箱。');
}
function currentUser(){return sb?.auth?.getUser?sb.auth.getUser():Promise.resolve({data:{user:null}});}
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
 const payload={scenario,radarContext:{generatedAt:radar.generated_at||null,state:radar.state||{},events:(radar.events||[]).slice(0,20),market:(radar.state?.finance?.market||[]).slice(0,20)},evidenceRegistry:registry,recordedAt:new Date().toISOString()};
 const row={task_id:String(task.id),user_id:user.id,status:'RECORDED',scenario_code:scenario.code||null,activation_state:scenario.activationState||null,trigger_score:scenario.triggerScore??null,confidence:scenario.confidence||null,evidence_count:Array.isArray(scenario.evidenceDrivers)?scenario.evidenceDrivers.length:null,payload};
 const {error}=await sb.from('scenario_task_runs').insert(row);
 if(error)console.warn('scenario run save failed',error.message);
};
const oldArchive=window.archiveTask;
window.archiveTask=async function(task){const row=oldArchive(task); await window.syncTaskToServer(row); return row;};
function renderAuthState(user){
 const box=document.getElementById('authBox'); if(!box)return;
 if(user) box.innerHTML='<div class="status">已登录：<b>'+esc(user.email||'账号')+'</b>。历史推演自动云端保存。 <button id="authLogout">退出登录</button></div><div class="mini muted">账号跨设备同步，不再需要保存同步密钥。</div>';
 else authPanel();
 const lo=document.getElementById('authLogout'); if(lo)lo.onclick=async()=>{await sb.auth.signOut();msg('已退出登录。')};
}
async function renderTaskRuns(taskId){
 const box=document.getElementById('taskRunsList'); if(!box||!taskId||!sb)return;
 const {data,error}=await sb.from('scenario_task_runs').select('id,observed_at,status,scenario_code,activation_state,trigger_score,confidence,evidence_count,payload').eq('task_id',String(taskId)).order('observed_at',{ascending:false}).limit(30);
 if(error){box.innerHTML='<div class="card muted">运行历史读取失败。</div>';return;}
 const rows=data||[];
 box.innerHTML=rows.length?rows.map((r,i)=>{
   const p=r.payload||{}, sc=p.scenario||{};
   const ctx=p.radarContext||{};
   const ev=(sc.evidenceDrivers||[]).filter(x=>x.kind==='EVENT').slice(0,4).map(x=>esc(x.title||x.id)).join('；');
   return '<article class="card"><b>#'+(rows.length-i)+' · '+esc(r.scenario_code||'未标注')+' · '+esc(r.activation_state||'WATCH')+' · '+Number(r.trigger_score||0).toFixed(2)+'</b><div class="muted mini">运行时间：'+esc(r.observed_at||'')+' · 置信度：'+esc(r.confidence||'—')+' · 证据：'+Number(r.evidence_count||0)+'</div><div class="mini">当时雷达：'+esc(ctx.generatedAt||'未知')+'</div><div class="mini">直接事件：'+esc(ev||'暂无')+'</div><div class="mini muted">记录包含当时态势、事件、市场与证据快照，可用于与后续运行对照。</div></article>';
 }).join(''):'<div class="card muted">这个任务还没有服务器运行记录。完成一次推演后会自动留下审计记录。</div>';
}
function ensureTaskRunsPanel(){
 if(document.getElementById('taskRunsPanel'))return;
 const anchor=document.getElementById('taskArchive');
 if(!anchor)return;
 const p=document.createElement('section');p.id='taskRunsPanel';p.className='panel';
 p.innerHTML='<div class="title">🧾 推演运行历史 · 第二阶段</div><div class="mini muted">每次运行保存当时的雷达时间、态势、关键事件、市场快照、剧本状态和证据驱动。这里记录历史事实，不把后来的信息倒灌回过去。</div><div id="taskRunsList" class="actions" style="margin-top:10px"><div class="card muted">选择或运行一个任务后加载。</div></div>';
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
 const oldRun=window.runScenarioTask;
 window.runScenarioTask=function(task){
   const result=oldRun(task);
   setTimeout(async()=>{
     const sc=window.__selectedScenario;
     if(sc){ await window.saveScenarioRun(task,sc); await renderTaskRuns(task.id); }
   },250);
   return result;
 };
 ensureTaskRunsPanel();
 window.renderTaskArchive();
}
function initAuth(){
 authPanel();
 sb.auth.onAuthStateChange(async(_event,session)=>{
   renderAuthState(session?.user||null);
   if(session?.user){await cloudPull();patchSandboxHooks();}
 });
 sb.auth.getSession().then(async({data:{session}})=>{renderAuthState(session?.user||null);if(session?.user){await cloudPull();patchSandboxHooks();}});
}
authLoad();
})();