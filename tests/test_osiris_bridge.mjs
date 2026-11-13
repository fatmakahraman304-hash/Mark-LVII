import test from 'node:test';
import assert from 'node:assert/strict';
import { installJarvisBridge } from '../integrations/osiris/jarvis-bridge.mjs';
const token = 'a'.repeat(64);
let counter = 0;
const id = () => (++counter).toString(16).padStart(32, '0');
function fixture(hostname = '127.0.0.1') {
  const host = { location: {hostname, protocol:'http:'}, setTimeout: (fn, ms) => setTimeout(fn, Math.min(ms, 3)) };
  let layers = { earthquakes:false, flights:true }, view = {lat:20,lng:0,zoom:2.5};
  const site = { layers:()=>layers, view:()=>view,
    setLayers:(on,off)=>setTimeout(()=>{for(const k of on) layers[k]=true;for(const k of off) layers[k]=false;},1),
    flyTo:(lat,lng,zoom)=>setTimeout(()=>{view={lat,lng,zoom}},1),
    geocode:async place=>place==='missing'?null:{name:place,lat:35.12,lng:33.94},
  };
  const dispose=installJarvisBridge(site,host);
  return {host,site,dispose,api:host.__jarvisOsiris};
}
async function result(api,command) {
  command={...command,id:id()};
  const initial=api.dispatch(token,command);
  if(initial.status==='failed') return initial;
  for(let i=0;i<100;i++) {
    const value=api.read(token,command.id);
    if(value.status!=='pending')return value;
    await new Promise(resolve=>setTimeout(resolve,4));
  }
  throw Error('test timeout');
}
test('bridge never installs on remote origin',()=>assert.equal(fixture('example.com').api,undefined));
test('session guard, command allowlist and bounds',()=>{
 const {api}=fixture(); api.bind(token);
 assert.equal(api.dispatch('bad',{id:id(),kind:'status'}).status,'failed');
 for(const command of [{kind:'shell'}, {kind:'layers',layers:['__proto__']},{kind:'zoom',delta:NaN},{kind:'locate',place:''}])
  assert.equal(api.dispatch(token,{id:id(),...command}).status,'failed');
});
test('state is confirmed after asynchronous layer update; clearing turns all off',async()=>{
 const {api}=fixture();api.bind(token);
 assert.deepEqual((await result(api,{kind:'layers',layers:['earthquakes']})).state.layers,['earthquakes']);
 assert.deepEqual((await result(api,{kind:'layers',layers:[]})).state.layers,[]);
});
test('locate and zoom verify actual camera state; missing place fails',async()=>{
 const {api}=fixture();api.bind(token);
 assert.equal((await result(api,{kind:'locate',place:'Gazimağusa'})).state.view.lat,35.12);
 assert.equal((await result(api,{kind:'zoom',delta:2})).state.view.zoom,12);
 assert.equal((await result(api,{kind:'locate',place:'missing'})).status,'failed');
});
test('unchanged UI reports unverified rather than done',async()=>{
 const {api,site}=fixture();site.setLayers=()=>{};api.bind(token);
 assert.equal((await result(api,{kind:'layers',layers:['earthquakes']})).status,'unverified');
});
test('session rotation cancels delayed geocode before it moves map',async()=>{
 const {api,site}=fixture();let resolve;
 site.geocode=()=>new Promise(r=>resolve=r);let moves=0;site.flyTo=()=>moves++;
 api.bind(token);api.dispatch(token,{id:id(),kind:'locate',place:'Nicosia'});
 api.bind('b'.repeat(64));resolve({lat:35,lng:33});
 await new Promise(r=>setTimeout(r,10));assert.equal(moves,0);
});
test('duplicate request is idempotent and disposal removes capability',async()=>{
 const {api,site,dispose,host}=fixture();api.bind(token);
 let calls=0;const original=site.setLayers;site.setLayers=(...args)=>{calls++;original(...args)};
 const command={id:id(),kind:'layers',layers:[]};api.dispatch(token,command);api.dispatch(token,command);
 await new Promise(r=>setTimeout(r,10));assert.equal(calls,1);
 dispose();assert.equal(host.__jarvisOsiris,undefined);
});
