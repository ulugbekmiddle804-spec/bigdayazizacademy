/**
 * Cloudflare Pages Function: forwards every /api/* request to the Django backend on Railway.
 *
 * The browser only ever talks to the Pages domain, so the admin session cookie and CSRF
 * work exactly as with nginx (no CORS, no third-party cookies blocked by Safari).
 *
 * Pages → Settings → Environment variables:
 *   BACKEND_URL   https://<your-service>.up.railway.app   (required)
 *   PROXY_SECRET  same random string as on Railway         (recommended: passes the visitor's real IP)
 */
interface Env {
  BACKEND_URL?: string;
  PROXY_SECRET?: string;
}

interface Ctx {
  request: Request;
  env: Env;
}

// Headers that must not be copied from the visitor's request.
const DROP = ["host", "cf-connecting-ip", "cf-ipcountry", "cf-ray", "cf-visitor", "x-forwarded-host",
  "x-forwarded-proto", "x-real-ip", "x-client-ip", "x-proxy-secret"];

export const onRequest = async ({ request, env }: Ctx): Promise<Response> => {
  const backend = (env.BACKEND_URL || "").replace(/\/+$/, "");
  if (!backend) {
    return Response.json({ detail: "BACKEND_URL sozlanmagan (Cloudflare Pages → Settings)." }, { status: 500 });
  }

  const url = new URL(request.url);
  const target = backend + url.pathname + url.search;

  const headers = new Headers(request.headers);
  for (const h of DROP) headers.delete(h);
  headers.set("X-Forwarded-Host", url.host);
  headers.set("X-Forwarded-Proto", "https");
  const ip = request.headers.get("CF-Connecting-IP");
  if (ip && env.PROXY_SECRET) {
    headers.set("X-Client-IP", ip);
    headers.set("X-Proxy-Secret", env.PROXY_SECRET);
  }

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      redirect: "manual",
    });
  } catch {
    return Response.json({ detail: "Server bilan aloqa yo'q. Birozdan so'ng qayta urinib ko'ring." }, { status: 502 });
  }

  const out = new Response(upstream.body, upstream); // keeps status and every Set-Cookie header
  out.headers.set("Cache-Control", upstream.headers.get("Cache-Control") || "no-store");
  return out;
};
