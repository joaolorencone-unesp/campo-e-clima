// Offline test: only local synthetic weather values. Never writes data to site/.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../site/static/app.js'),'utf8');
const start=source.indexOf('const FORECAST_LIVE_URL=');
const end=source.indexOf('let refreshInProgress=',start);
assert(start>=0&&end>start);
const code=source.slice(start,end);
const n=48;
const time=new Date(Date.now()-4*3600*1000).toISOString().slice(0,16);
const payload={
 utc_offset_seconds:-14400,latitude:-23.063,longitude:-54.188,
 hourly:{time:Array.from({length:n},(_,i)=>'2026-10-26T'+String(i%24).padStart(2,'0')+':00'),temperature_2m:Array(n).fill(24)},
 daily:{time:Array.from({length:14},(_,i)=>'2026-10-'+String((i%6)+26).padStart(2,'0'))},
 current:{time,temperature_2m:24,relative_humidity_2m:65,wind_speed_10m:6}
};
let requests=0;
const ctx={
  URLSearchParams,Date,AbortController,setTimeout,clearTimeout,
  fetch:async(url)=>{
    requests++;
    const q=new URL(url).searchParams;
    assert.equal(q.get('timezone'),'America/Campo_Grande');
    assert.equal(q.get('forecast_days'),'14');
    assert(q.get('hourly').includes('wind_gusts_10m'));
    return {ok:true,json:async()=>payload};
  }
};
vm.createContext(ctx);
(async()=>{
 const f=vm.runInContext(code+'\nfetchDirectForecast',ctx);
 const got=await f();
 assert.equal(got.utc_offset_seconds,-14400);
 assert.equal(got.hourly.time.length,n);
 assert(got.model_used.includes('consulta direta'));
 assert.equal(requests,1);
 payload.utc_offset_seconds=0;
 await assert.rejects(()=>f(),/Fuso horário/);
 console.log('PASS: consulta determinística direta, atualização real e validação de fuso.');
})().catch(e=>{console.error(e);process.exit(1)});
