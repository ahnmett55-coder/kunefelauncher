// KünefeLauncher bulut: TAB logosu + arkadaşlar + mesajlaşma
// D1 bağlıysa (binding adı: DB) kalıcıdır; bağlı değilse bellekte çalışır (Worker yeniden başlarsa sıfırlanır).
let S = { users: {}, friends: {}, msgs: [], nextId: 1, seen: {}, gseen: {} };
let loaded = false;
const J = (o, st = 200) => new Response(JSON.stringify(o), { status: st, headers: { "content-type": "application/json", "access-control-allow-origin": "*" } });
const VALID = /^\w{1,16}$/;

async function load(env) {
  if (!env.DB) return;
  try {
    await env.DB.exec("CREATE TABLE IF NOT EXISTS st (k TEXT PRIMARY KEY, v TEXT)");
    const r = await env.DB.prepare("SELECT v FROM st WHERE k='s'").first();
    if (r) S = Object.assign(S, JSON.parse(r.v));
  } catch (e) {}
}
async function save(env) {
  if (!env.DB) return;
  try {
    await env.DB.prepare("INSERT INTO st(k,v) VALUES('s',?1) ON CONFLICT(k) DO UPDATE SET v=?1").bind(JSON.stringify(S)).run();
  } catch (e) {}
}
async function sha(t) {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t));
  return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("");
}
const fkey = (a, b) => [a, b].sort().join("|");
const now = () => Math.floor(Date.now() / 1000);

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    if (req.method === "OPTIONS") return J({});
    await load(env);
    const t = now();
    // --- eski uç noktalar (TAB logosu)
    if (u.pathname === "/ping" && req.method === "POST") {
      const n = (u.searchParams.get("name") || "").toLowerCase();
      if (!VALID.test(n)) return J({ ok: false }, 400);
      S.gseen[n] = t;
      S.seen[n] = t;
      return J({ ok: true });
    }
    if (u.pathname === "/online") {
      for (const k of Object.keys(S.gseen)) if (t - S.gseen[k] > 90) delete S.gseen[k];
      return J({ ok: true, names: Object.keys(S.gseen) });
    }
    if (req.method !== "POST") return new Response("KunefeCloud");
    // --- kimlikli uç noktalar
    let b;
    try { b = await req.json(); } catch (e) { return J({ ok: false, err: "json" }, 400); }
    const me = String(b.name || "").toLowerCase();
    const tok = String(b.token || "");
    if (!VALID.test(me) || tok.length < 16) return J({ ok: false, err: "kimlik" }, 400);
    const h = await sha(tok);
    if (!S.users[me]) { S.users[me] = h; }
    else if (S.users[me] !== h) return J({ ok: false, err: "Bu ad başka bir launcher'a ait" }, 403);
    S.seen[me] = t;
    let mut = true;
    const p = u.pathname;
    const isFriend = o => S.friends[fkey(me, o)] === "ok";
    let out = { ok: true };
    if (p === "/friends") {
      mut = false;
      const fr = [], inc = [], outg = [];
      for (const [k, v] of Object.entries(S.friends)) {
        const [a, c] = k.split("|");
        if (a !== me && c !== me) continue;
        const o = a === me ? c : a;
        if (v === "ok") {
          const unread = S.msgs.filter(m => m.to === me && m.from === o && !m.read).length;
          fr.push({ name: o, online: t - (S.seen[o] || 0) < 90, unread });
        } else if (v.startsWith("req:")) {
          (v.slice(4) === me ? outg : inc).push(o);
        }
      }
      out = { ok: true, friends: fr, incoming: inc, outgoing: outg };
    } else if (p === "/friend/add") {
      const o = String(b.to || "").toLowerCase();
      if (!VALID.test(o) || o === me) return J({ ok: false, err: "Geçersiz ad" }, 400);
      if (!S.users[o]) return J({ ok: false, err: "Bu oyuncu henüz KünefeLauncher kullanmamış" }, 404);
      const k = fkey(me, o), v = S.friends[k];
      if (v === "ok") out = { ok: true, msg: "Zaten arkadaşsınız" };
      else if (v && v.startsWith("req:") && v.slice(4) === o) { S.friends[k] = "ok"; out = { ok: true, msg: "Arkadaş oldunuz" }; }
      else { S.friends[k] = "req:" + me; out = { ok: true, msg: "İstek gönderildi" }; }
    } else if (p === "/friend/accept") {
      const o = String(b.from || "").toLowerCase(), k = fkey(me, o);
      if (S.friends[k] === "req:" + o) S.friends[k] = "ok"; else return J({ ok: false, err: "İstek yok" }, 404);
    } else if (p === "/friend/remove") {
      delete S.friends[fkey(me, String(b.other || "").toLowerCase())];
    } else if (p === "/msg/send") {
      const o = String(b.to || "").toLowerCase(), text = String(b.text || "").trim().slice(0, 300);
      if (!isFriend(o) || !text) return J({ ok: false, err: "Sadece arkadaşlara yazabilirsin" }, 403);
      S.msgs.push({ id: S.nextId++, from: me, to: o, text, ts: t, read: false });
      if (S.msgs.length > 1500) S.msgs.splice(0, S.msgs.length - 1500);
    } else if (p === "/msg/list") {
      const o = String(b.with || "").toLowerCase(), after = +b.after || 0;
      if (!isFriend(o)) return J({ ok: false, err: "Arkadaş değil" }, 403);
      const l = S.msgs.filter(m => m.id > after && ((m.from === me && m.to === o) || (m.from === o && m.to === me)));
      mut = false;
      for (const m of l) if (m.to === me && !m.read) { m.read = true; mut = true; }
      out = { ok: true, msgs: l.map(m => ({ id: m.id, from: m.from, text: m.text, ts: m.ts })) };
    } else if (p === "/hello") {
      mut = false;
    } else {
      return J({ ok: false, err: "yok" }, 404);
    }
    if (mut) await save(env);
    return J(out);
  },
};
