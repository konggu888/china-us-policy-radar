const RADAR_STATE_URL = "https://raw.githubusercontent.com/konggu888/china-us-policy-radar/main/data/scenario_state.json";

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors = {
      "Access-Control-Allow-Origin": origin || "*",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Vary": "Origin"
    };
    if (request.method === "OPTIONS") return new Response(null,{headers:cors});
    if (!env.SCENARIO_TASKS) return json({error:"KV_NOT_CONFIGURED"},500,cors);
    if (!authorized(request,env)) return json({error:"UNAUTHORIZED"},401,cors);
    try {
      if (request.method === "GET") {
        const tasks = await env.SCENARIO_TASKS.get("tasks","json");
        const safe = Array.isArray(tasks)?tasks:[];
        const withRuns = await Promise.all(safe.map(async t => ({
          ...t, runs: (await env.SCENARIO_TASKS.get("runs:"+t.id,"json")) || []
        })));
        return json({schema_version:"scenario-task-registry-v2",tasks:withRuns},200,cors);
      }
      if (request.method === "POST") {
        const body = await request.json();
        const incoming = Array.isArray(body?.tasks) ? body.tasks : (body?.task ? [body.task] : []);
        if (!incoming.length) return json({error:"NO_TASKS"},400,cors);
        const old = await env.SCENARIO_TASKS.get("tasks","json");
        const map = new Map((Array.isArray(old)?old:[]).filter(x=>x?.id&&x?.event).map(x=>[x.id,x]));
        const now = new Date().toISOString();
        for (const t of incoming) {
          if (!t?.id || !t?.event) continue;
          map.set(String(t.id),{...t,updatedAt:now});
        }
        const tasks = Array.from(map.values()).sort((a,b)=>String(b.updatedAt||b.createdAt||"").localeCompare(String(a.updatedAt||a.createdAt||""))).slice(0,200);
        await env.SCENARIO_TASKS.put("tasks",JSON.stringify(tasks));
        return json({ok:true,count:tasks.length,saved:incoming.length},200,cors);
      }
      return json({error:"METHOD_NOT_ALLOWED"},405,cors);
    } catch(e) { return json({error:"BAD_REQUEST",message:String(e?.message||e)},400,cors); }
  },
  async scheduled(event, env, ctx) {
    ctx.waitUntil(monitorTasks(env));
  }
};

function authorized(request,env) {
  const auth=request.headers.get("Authorization")||"";
  return Boolean(env.SCENARIO_TASK_TOKEN) && auth==="Bearer "+env.SCENARIO_TASK_TOKEN;
}
async function monitorTasks(env) {
  const tasks=await env.SCENARIO_TASKS.get("tasks","json");
  if(!Array.isArray(tasks)||!tasks.length)return;
  let state;
  try {
    const r=await fetch(RADAR_STATE_URL,{headers:{"User-Agent":"china-us-policy-radar-scenario-worker/1.0"}});
    if(!r.ok)return;
    state=await r.json();
  } catch(e){return;}
  const scenarios=state?.scenarioTree?.scenarios||state?.scenarios||[];
  const now=new Date().toISOString();
  for(const task of tasks.slice(0,200)){
    const code=task.modelCode||task.selectedScenarioCode;
    const scenario=scenarios.find(s=>String(s.code)===String(code));
    const run={
      runId: now+"-"+String(task.id),
      observedAt:now,
      radarGeneratedAt:state.generatedAt||state.generated_at||null,
      scenarioCode:code||null,
      activationState:scenario?.activationState||"UNKNOWN",
      triggerScore:scenario?.triggerScore??null,
      confidence:scenario?.confidence||"UNKNOWN",
      evidenceCount:Array.isArray(scenario?.evidenceDrivers)?scenario.evidenceDrivers.length:null,
      triggerEvidence:scenario?.triggerEvidence||[],
      counterSignals:scenario?.counterSignals||[],
      status:scenario?"OBSERVED":"SCENARIO_NOT_FOUND",
      interpretation:"定时记录当前雷达状态，用于历史跟踪；不表示发生概率或因果关系。"
    };
    const key="runs:"+task.id;
    const old=await env.SCENARIO_TASKS.get(key,"json");
    const runs=Array.isArray(old)?old:[];
    runs.push(run);
    await env.SCENARIO_TASKS.put(key,JSON.stringify(runs.slice(-365)));
  }
}
function json(data,status,headers={}) {
  return new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json; charset=utf-8",...headers}});
}
