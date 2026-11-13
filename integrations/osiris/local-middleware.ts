/** JARVIS local profile: loopback only; map/read endpoints, no scanner or ingest. */
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
const READ = new Set([
  'health', 'stats', 'geo', 'geosearch', 'flights', 'aircraft', 'maritime',
  'satellites', 'earthquakes', 'fires', 'weather', 'live-news', 'news',
  'cctv', 'balloons', 'infrastructure', 'radiation', 'space-weather',
  'gdelt', 'gdelt-events', 'cloudflare-radar', 'rain', 'wind',
]);
export function middleware(request: NextRequest) {
  const host = request.nextUrl.hostname;
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(host))
    return new NextResponse('Loopback only', { status: 403 });
  if (!['GET', 'HEAD'].includes(request.method))
    return new NextResponse('Read-only local map', { status: 405 });
  const path = request.nextUrl.pathname;
  if (path.startsWith('/api/')) {
    const endpoint = path.slice(5);
    if (!READ.has(endpoint)) return new NextResponse('Disabled in JARVIS local profile', { status: 403 });
  }
  return NextResponse.next();
}
export const config = { matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'] };
