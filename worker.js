export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    const h = { "content-type": "application/json", "access-control-allow-origin": "*" };
    if (u.pathname === "/ping" && req.method === "POST") {
      const n = (u.searchParams.get("name") || "").toLowerCase();
      if (!/^\w{1,16}$/.test(n)) return new Response('{"ok":false}', { status: 400, headers: h });
      await env.ONLINE.put("u:" + n, "1", { expirationTtl: 120 });
      return new Response('{"ok":true}', { headers: h });
    }
    if (u.pathname === "/online") {
      const l = await env.ONLINE.list({ prefix: "u:" });
      return new Response(JSON.stringify({ ok: true, names: l.keys.map(k => k.name.slice(2)) }), { headers: h });
    }
    return new Response("KunefeOnline", { headers: h });
  },
};
