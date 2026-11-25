// KV gerektirmeyen basit surum (bellekte tutar; Worker yeniden baslarsa liste birkac dakikada kendini toparlar)
const ONLINE = new Map();
export default {
  async fetch(req) {
    const u = new URL(req.url);
    const h = { "content-type": "application/json", "access-control-allow-origin": "*" };
    const now = Date.now();
    for (const [k, t] of ONLINE) if (now - t > 90000) ONLINE.delete(k);
    if (u.pathname === "/ping" && req.method === "POST") {
      const n = (u.searchParams.get("name") || "").toLowerCase();
      if (!/^\w{1,16}$/.test(n)) return new Response('{"ok":false}', { status: 400, headers: h });
      ONLINE.set(n, now);
      return new Response('{"ok":true}', { headers: h });
    }
    if (u.pathname === "/online") return new Response(JSON.stringify({ ok: true, names: [...ONLINE.keys()] }), { headers: h });
    return new Response("KunefeOnline", { headers: h });
  },
};
