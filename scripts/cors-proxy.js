// Cloudflare Worker — CORS proxy for Steam API
// Deploy: wrangler deploy or copy-paste into Cloudflare dashboard
export default {
  async fetch(request) {
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
    return new Response(resp.body, {
      status: resp.status,
      statusText: resp.statusText,
      headers,
    });
  },
};
