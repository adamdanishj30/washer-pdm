// Cloudflare Pages Function: /api/live
// Edge Cache Proxy for Firebase Realtime Database
// Caches live telemetry for 4 seconds at the edge so multiple visitors/bots
// share a single cached response, protecting Firebase free-tier quota.

export async function onRequestGet(context) {
  const cacheUrl = new URL(context.request.url);
  const cacheKey = new Request(cacheUrl.toString(), context.request);
  const cache = caches.default;

  // Check Cloudflare Edge Cache first
  let response = await cache.match(cacheKey);
  if (!response) {
    try {
      const fbUrl = 'https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app/live.json';
      const fbRes = await fetch(fbUrl, {
        headers: { 'Accept': 'application/json' }
      });
      const data = await fbRes.text();

      response = new Response(data, {
        status: fbRes.status,
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Cache-Control': 'public, max-age=2, s-maxage=2'
        }
      });

      // Store in Cloudflare edge cache for 2 seconds
      context.waitUntil(cache.put(cacheKey, response.clone()));
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 502,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
    }
  }

  return response;
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400'
    }
  });
}
