/* Browser integration against the separately collected audit snapshot. No external API calls. */
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const base=process.env.CAMPO_PREVIEW_URL||'http://127.0.0.1:8778';
 const output=process.env.CAMPO_BROWSER_OUTPUT||'docs/RELEASES/premerge/browser';
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.EDGE_EXECUTABLE||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const report={base,checked_at_utc:new Date().toISOString(),source:'Isolated real weather collected on 2026-10-29; not official data',cases:[]};
 for(const mobile of [false,true]){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},locale:'pt-BR',timezoneId:'America/Campo_Grande',isMobile:mobile});
  // Permit static plot libraries, but never spend meteorological API quota from the browser.
  await context.route(/.*(open-meteo\.com|apitempo\.inmet\.gov\.br|api\.openweathermap\.org).*/,r=>r.abort());
  const page=await context.newPage(),errors=[],missing=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)missing.push({url:r.url(),status:r.status()});});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#last-updated')?.textContent.includes('coleta mais antiga'),{timeout:30000});
  await page.locator('#tabs button[data-tab="extended"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#calendar .calday.gefs').length>0);
  const cells=await page.locator('#calendar .calday').count(),gefs=await page.locator('#calendar .calday.gefs').count();
  assert.equal(cells,30);assert.equal(gefs,16);
  assert.match(await page.locator('#calendar-coverage').innerText(),/30 de 30 datas.*16 dias GEFS/);
  assert.match(await page.locator('#calendar .calday.gefs').first().innerText(),/UM modelo · 30 membros/);
  const freshness=await page.locator('#last-updated').innerText();
  assert.match(freshness,/coleta mais antiga em uso/);
  await page.waitForFunction(()=>document.querySelector('#extended-gefs-plot')?.classList.contains('js-plotly-plot'));
  assert.doesNotMatch(await page.locator('#extended-gefs-plot').innerText(),/Sem dados válidos/);
  await page.locator('#extended').screenshot({path:path.join(output,`calendar_${mobile?'mobile':'desktop'}.png`)});
  await page.locator('#tabs button[data-tab="precision"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#precision-kpis .agro-kpi').length===4);
  assert.match(await page.locator('#precision-status').innerText(),/Ainda não há amostras/);
  await page.locator('#precision-location').selectOption('diamantino');
  assert.match(await page.locator('#precision-provenance').innerText(),/Diamantino/);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
  assert.equal(overflow,false);assert.deepEqual(errors,[]);assert.deepEqual(missing,[]);
  report.cases.push({mobile,calendar_dates:cells,gefs_days:gefs,gefs_members:30,freshness,js_errors:errors,missing_local_resources:missing,horizontal_overflow:overflow,precision_no_observations:true});
  await context.close();
 }
 await browser.close();fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exit(1)});
