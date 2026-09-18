export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors = {
      "Access-Control-Allow-Origin": origin || "*",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Vary": "Origin"
    };
    if (request.method === "OPTIONS") return new Response(null, {headers:cors});
    if (!env.SCENARIO_TASKS) return json({error:"KV_NOT_CONFIGURED"},500,cors);
    const auth = request.headers.get("Authorization") || "";
    if (!env.SCENARIO_TASK_TOKEN || auth !== "Bearer " + env.SCENARIO_TASK_TOKEN) {
      return json({error:"UNAUTHORIZED"},401,cors);
    }
    try {
      if (request.method === "GET") {
        const tasks = await env.SCENARIO_TASKS.get("tasks","json");
        return json({schema_version:"scenario-task-registry-v1",tasks:Array.isArray(tasks)?tasks:[]},200,cors);
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
          map.set(String(t.id), {...t,updatedAt:now});
        }
        const tasks = Array.from(map.values())
          .sort((a,b)=>String(b.updatedAt||b.createdAt||"").localeCompare(String(a.updatedAt||a.createdAt||"")))
          .slice(0,200);
        await env.SCENARIO_TASKS.put("tasks",JSON.stringify(tasks));
        return json({ok:true,count:tasks.length,saved:incoming.length},200,cors);
      }
      return json({error:"METHOD_NOT_ALLOWED"},405,cors);
    } catch (e) {
      return json({error:"BAD_REQUEST",message:String(e?.message||e)},400,cors);
    }
  }
};
function json(data,status,headers={}) {
  return new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json; charset=utf-8",...headers}});
}
