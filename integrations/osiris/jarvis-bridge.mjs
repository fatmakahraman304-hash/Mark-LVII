/** Narrow, one-way local map adapter. No host API, shell, credentials or web channel. */
export function installJarvisBridge(site, host = window) {
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(host.location.hostname) ||
      host.location.protocol !== 'http:') return () => {};
  let session = '';
  let generation = 0;
  let busy = false;
  const receipts = new Map();
  const snapshot = () => ({
    layers: Object.entries(site.layers()).filter(([, on]) => on).map(([key]) => key).sort(),
    view: { lat: site.view().lat, lng: site.view().lng, zoom: site.view().zoom },
  });
  const finite = (n, lo, hi) => typeof n === 'number' && Number.isFinite(n) && n >= lo && n <= hi;
  const api = {
    version: 1,
    bind(token) {
      if (typeof token !== 'string' || token.length < 32 || token.length > 128) return false;
      if (session !== token) { generation++; receipts.clear(); busy = false; }
      session = token;
      return true;
    },
    read(token, id) {
      if (!session || token !== session) return { status: 'failed', error: 'session' };
      return receipts.get(id) || { status: 'unknown' };
    },
    dispatch(token, command) {
      if (!session || token !== session) return { status: 'failed', error: 'session' };
      if (!command || !/^[a-f0-9]{32}$/.test(command.id || '')) return { status: 'failed', error: 'id' };
      if (receipts.has(command.id)) return receipts.get(command.id);
      if (busy) return { status: 'failed', error: 'busy' };
      const fail = error => ({ status: 'failed', error, id: command.id });
      if (!['layers', 'locate', 'zoom', 'status'].includes(command.kind)) return fail('unsupported');
      if (command.kind === 'layers' && (!Array.isArray(command.layers) ||
          command.layers.length > 64 || command.layers.some(k => typeof k !== 'string' || !Object.hasOwn(site.layers(), k))))
        return fail('layers');
      if (command.kind === 'locate' && !(typeof command.place === 'string' && command.place.trim().length > 0 && command.place.length <= 120))
        return fail('place');
      if (command.kind === 'zoom' && !finite(command.delta, -3, 3)) return fail('zoom');
      while (receipts.size >= 32) receipts.delete(receipts.keys().next().value);
      receipts.set(command.id, { id: command.id, status: 'pending' });
      busy = true;
      const ownGeneration = generation;
      const valid = () => ownGeneration === generation && session === token;
      const record = result => {
        if (valid()) { receipts.set(command.id, { id: command.id, ...result }); busy = false; }
      };
      (async () => {
        try {
          let target;
          if (command.kind === 'layers') {
            const desired = new Set(command.layers);
            site.setLayers(command.layers, Object.keys(site.layers()).filter(k => !desired.has(k)));
          } else if (command.kind === 'locate') {
            const hit = await Promise.race([
              site.geocode(command.place.trim()),
              new Promise((_, reject) => host.setTimeout(() => reject(Error('geocode_timeout')), 8000)),
            ]);
            if (!valid()) return;
            if (!hit || !finite(hit.lat, -85, 85) || !finite(hit.lng, -180, 180)) throw Error('place_not_found');
            target = { lat: hit.lat, lng: hit.lng, zoom: 10 };
            site.flyTo(target.lat, target.lng, target.zoom);
          } else if (command.kind === 'zoom') {
            const current = site.view();
            target = { lat: current.lat, lng: current.lng, zoom: Math.max(1, Math.min(18, current.zoom + command.delta)) };
            if (!finite(target.lat, -85, 85) || !finite(target.lng, -180, 180)) throw Error('view');
            site.flyTo(target.lat, target.lng, target.zoom);
          }
          for (let attempt = 0; attempt < 60 && valid(); attempt++) {
            const state = snapshot();
            const matches = command.kind === 'status' ||
              (command.kind === 'layers' && JSON.stringify(state.layers) === JSON.stringify([...new Set(command.layers)].sort())) ||
              (target && Math.abs(state.view.lat - target.lat) < .02 &&
                Math.abs(state.view.lng - target.lng) < .02 && Math.abs(state.view.zoom - target.zoom) < .1);
            if (matches) { record({ status: 'done', state }); return; }
            await new Promise(resolve => host.setTimeout(resolve, 100));
          }
          record({ status: 'unverified', error: 'state_timeout', state: snapshot() });
        } catch (error) { record({ status: 'failed', error: String(error.message || error).slice(0, 100) }); }
      })();
      return receipts.get(command.id);
    },
  };
  host.__jarvisOsiris = api;
  return () => {
    generation++; session = '';
    if (host.__jarvisOsiris === api) delete host.__jarvisOsiris;
  };
}
