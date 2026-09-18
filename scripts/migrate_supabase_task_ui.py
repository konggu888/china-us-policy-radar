from pathlib import Path

p = Path("scenario.html")
s = p.read_text(encoding="utf-8")
api = "https://ctiebkgsfmimedkoiapw.supabase.co/functions/v1/scenario-tasks"

old_status = "任务保存在本机浏览器中。刷新、关闭页面、重新推演其他问题都不会删除它。重新打开旧任务时，会使用最新雷达数据重新计算；“样本不足”只表示等待后续证据。"
s = s.replace(old_status, "任务现在同时保存在本机与 Supabase。刷新、关闭页面、重新推演其他问题都不会删除；使用同一同步密钥可在另一台设备继续。")

start = s.index("const TASK_API_KEY='chinaUsPolicyRadar.scenarioTaskApi.v1';")
end = s.index("const TASK_LIMIT=50;", start)
new = f"""const TASK_API_URL='{api}';
const TASK_TOKEN_KEY='chinaUsPolicyRadar.scenarioTaskSupabaseToken.v1';
function taskApi(){{return TASK_API_URL;}}
function taskToken(){{return localStorage.getItem(TASK_TOKEN_KEY)||'';}}
function createTaskToken(){{
  const bytes=new Uint8Array(32); crypto.getRandomValues(bytes);
  let bin=''; for(const b of bytes) bin+=String.fromCharCode(b);
  return btoa(bin).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');
}}
function ensureTaskToken(){{
  let token=taskToken();
  if(!token){{token=createTaskToken();localStorage.setItem(TASK_TOKEN_KEY,token);}}
  return token;
}}
function showTaskToken(){{
  const token=ensureTaskToken();
  prompt('这是当前设备的 Supabase 推演同步密钥。换设备时输入同一密钥即可同步；不要公开发布。',token);
}}
async function syncTasksFromServer(){{
 const token=ensureTaskToken(); if(!token)return;
 try{{
  const r=await fetch(taskApi(),{{headers:{{Authorization:'Bearer '+token}}}});
  if(!r.ok)return;
  const p=await r.json(), incoming=Array.isArray(p.tasks)?p.tasks:[];
  const map=new Map(loadTaskArchive().map(t=>[t.id,t]));
  incoming.forEach(t=>{{if(t?.id&&t?.event)map.set(t.id,t);}});
  saveTaskArchive(Array.from(map.values()).sort((a,b)=>String(b.updatedAt||b.createdAt||'').localeCompare(String(a.updatedAt||a.createdAt||''))));
 }}catch(e){{console.warn('scenario task sync failed');}}
}}
async function syncTaskToServer(task){{
 const token=ensureTaskToken(); if(!token)return;
 try{{await fetch(taskApi(),{{method:'POST',headers:{{'Content-Type':'application/json',Authorization:'Bearer '+token}},body:JSON.stringify({{task}})}});}}
 catch(e){{console.warn('scenario task upload failed');}}
}}
"""
s = s[:start] + new + s[end:]

s = s.replace('<button onclick="setTaskApi()">设置服务器同步</button> ', '<button onclick="showTaskToken()">查看同步密钥</button> ')

old_end = "renderTaskArchive(); syncTasksFromServer().then(()=>{renderTaskArchive(); loadScenario().then(()=>{renderTaskArchive();const latest=loadTaskArchive()[0];if(latest)runScenarioTask(latest);});});"
new_end = "ensureTaskToken(); renderTaskArchive(); syncTasksFromServer().then(()=>{renderTaskArchive(); loadScenario().then(()=>{renderTaskArchive();});});"
if old_end not in s:
    raise SystemExit("final init marker missing")
s = s.replace(old_end, new_end)

p.write_text(s, encoding="utf-8")
print("Supabase task UI migration applied.")
