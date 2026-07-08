// Cloudflare Worker — CORS proxy for Steam API (with rate limiting)
// Deploy: wrangler deploy or copy-paste into Cloudflare dashboard

const RATE_LIMIT = new Map();

export default {
  async fetch(request) {
    const ip = request.headers.get('cf-connecting-ip') || 'unknown';
    const now = Date.now();
    const windowMs = 60000;
    const maxRequests = 30;

    const entry = RATE_LIMIT.get(ip) || { count: 0, reset: now + windowMs };
    if (now > entry.reset) { entry.count = 0; entry.reset = now + windowMs; }
    entry.count++;
    RATE_LIMIT.set(ip, entry);
    if (entry.count > maxRequests) {
      return new Response('Rate limit exceeded', { status: 429 });
    }

    const url = new URL(request.url);
    const target = url.searchParams.get('url');
    if (!target) {
      return new Response('Missing ?url= parameter', { status: 400 });
    }
    const resp = await fetch(target, {
      headers: { 'User-Agent': 'SteamLibraryExporter/1.0' },
    });
    const headers = new Headers(resp.headers);
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Access-Control-Allow-Methods', 'GET, OPTIONS');
    headers.set('X-RateLimit-Remaining', String(maxRequests - entry.count));
    return new Response(resp.body, {
      status: resp.status,
      statusText: resp.statusText,
      headers,
    });
  },
};
