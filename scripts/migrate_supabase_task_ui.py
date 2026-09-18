from pathlib import Path

p = Path("scenario.html")
s = p.read_text(encoding="utf-8")

# This migration is intentionally idempotent. Supabase account auth now owns
# identity/session state; the legacy device sync-token UI must not be revived.
old_status = "任务保存在本机浏览器中。刷新、关闭页面、重新推演其他问题都不会删除它。重新打开旧任务时，会使用最新雷达数据重新计算；“样本不足”只表示等待后续证据。"
new_status = "任务同时保存在本机与 Supabase。登录账号后历史推演自动云端保存，跨设备同步不再依赖手工保存同步密钥。重新打开旧任务时，会使用最新雷达数据重新计算；“样本不足”只表示等待后续证据。"
s = s.replace(old_status, new_status)

# Replace the legacy local sync-token block when it is still present.
marker = "const TASK_API_KEY='chinaUsPolicyRadar.scenarioTaskApi.v1';"
limit_marker = "const TASK_LIMIT=50;"
if marker in s and limit_marker in s:
    start = s.index(marker)
    end = s.index(limit_marker, start)
    api = "https://ctiebkgsfmimedkoiapw.supabase.co/functions/v1/scenario-tasks"
    block = f"""const TASK_API_URL='{api}';
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
function showTaskToken(){{ alert('请使用账号登录。云端历史由 Supabase 账号保存，不再需要手工同步密钥。'); }}
async function syncTasksFromServer(){{
  try{{
    const token=ensureTaskToken();
    const r=await fetch(taskApi(),{{headers:{{Authorization:'Bearer '+token}}}});
    if(!r.ok)return;
    const p=await r.json(), incoming=Array.isArray(p.tasks)?p.tasks:[];
    const map=new Map(loadTaskArchive().map(t=>[t.id,t]));
    incoming.forEach(t=>{{if(t?.id&&t?.event)map.set(t.id,t);}});
    saveTaskArchive(Array.from(map.values()).sort((a,b)=>String(b.updatedAt||b.createdAt||'').localeCompare(String(a.updatedAt||a.createdAt||''))));
  }}catch(e){{console.warn('scenario task sync failed');}}
}}
async function syncTaskToServer(task){{
  try{{
    const token=ensureTaskToken();
    await fetch(taskApi(),{{method:'POST',headers:{{'Content-Type':'application/json',Authorization:'Bearer '+token}},body:JSON.stringify({{task}})}})
  }}catch(e){{console.warn('scenario task upload failed');}}
}}
"""
    s = s[:start] + block + s[end:]

# Remove the obsolete manual-token button if the old migration left one behind.
s = s.replace('<button onclick="setTaskApi()">设置服务器同步</button> ', '')
s = s.replace('<button onclick="showTaskToken()">查看同步密钥</button> ', '')

p.write_text(s, encoding="utf-8")
print("Supabase task UI migration completed (idempotent).")
