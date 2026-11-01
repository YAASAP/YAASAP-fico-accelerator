// Cloudflare Worker : webhook Stripe -> clé d'accès envoyée par e-mail -> vérification.
// Secrets : STRIPE_WEBHOOK_SECRET, LICENCE_SECRET, BREVO_API_KEY ; variables : MAIL_FROM (expéditeur vérifié dans Brevo), SITE_URL ; KV : LICENCES.
const enc = new TextEncoder();
const hex = (b) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");

async function hmac(secret, data) {
  const k = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", k, enc.encode(data)));
}
function egal(a, b) {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}
export async function signatureStripeValide(corps, entete, secret, maintenant = Date.now() / 1000) {
  const p = Object.fromEntries((entete || "").split(",").map((s) => s.split("=")));
  if (!p.t || !p.v1 || Math.abs(maintenant - Number(p.t)) > 300) return false;
  return egal(await hmac(secret, `${p.t}.${corps}`), p.v1);
}
export async function creerCle(env, email, plan) {
  const ts = Date.now().toString(36).toUpperCase();
  const sig = (await hmac(env.LICENCE_SECRET, `${email}|${plan}|${ts}`)).slice(0, 16).toUpperCase();
  return `FA-${ts}-${sig}`;
}
const norm = (e) => String(e || "").trim().toLowerCase();
const json = (o, s = 200, h = {}) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json", ...h } });

async function envoyerMail(env, email, cle) {
  const r = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": env.BREVO_API_KEY, "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify({
      sender: { name: "FICO Accelerator", email: env.MAIL_FROM }, to: [{ email }], subject: "Votre accès FICO Accelerator",
      textContent: `Merci pour votre souscription.\n\nVotre clé d'accès : ${cle}\n\nActivez-la sur ${env.SITE_URL}/acces.html avec cette adresse e-mail (${email}).\n\nVous pouvez résilier à tout moment depuis le lien de votre reçu Stripe.`,
    }),
  });
  if (!r.ok) throw new Error(`mail ${r.status}`);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const cors = { "access-control-allow-origin": env.SITE_URL, "access-control-allow-headers": "content-type" };
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });

    if (url.pathname === "/webhook" && req.method === "POST") {
      const corps = await req.text();
      if (!(await signatureStripeValide(corps, req.headers.get("stripe-signature"), env.STRIPE_WEBHOOK_SECRET)))
        return json({ error: "signature" }, 400);
      const ev = JSON.parse(corps), o = ev.data.object;
      if (ev.type === "checkout.session.completed" && o.payment_status !== "unpaid") {
        const email = norm(o.customer_details?.email || o.customer_email);
        if (!email) return json({ error: "email" }, 400);
        const existant = JSON.parse((await env.LICENCES.get(`lic:${email}`)) || "null");
        let cle = existant?.key;
        if (!cle) {
          cle = await creerCle(env, email, "solo");
          await envoyerMail(env, email, cle);
        }
        await env.LICENCES.put(`lic:${email}`, JSON.stringify({ key: cle, plan: "solo", active: true }));
        if (o.customer) await env.LICENCES.put(`cus:${o.customer}`, email);
      } else if (ev.type === "customer.subscription.deleted" && o.customer) {
        const email = await env.LICENCES.get(`cus:${o.customer}`);
        const l = email && JSON.parse((await env.LICENCES.get(`lic:${email}`)) || "null");
        if (l) await env.LICENCES.put(`lic:${email}`, JSON.stringify({ ...l, active: false }));
      }
      return json({ received: true });
    }

    if (url.pathname === "/verify" && req.method === "POST") {
      const { email, key } = await req.json().catch(() => ({}));
      const l = JSON.parse((await env.LICENCES.get(`lic:${norm(email)}`)) || "null");
      const valid = !!(l && l.active && typeof key === "string" && egal(l.key, key.trim().toUpperCase()));
      return json(valid ? { valid: true, plan: l.plan } : { valid: false }, 200, cors);
    }
    return json({ error: "not found" }, 404, cors);
  },
};
