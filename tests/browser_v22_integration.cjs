/* Real local files. Failure cases intentionally block weather APIs after initial rendering. */
const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.EDGE_EXECUTABLE||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const base=process.env.CAMPO_PREVIEW_URL||'http://127.0.0.1:8777';
 const output='docs/RELEASES/integration-screenshots';fs.mkdirSync(output,{recursive:true});
 const report={base,checked_at_utc:new Date().toISOString(),weather_api_calls:0,cases:[]};
 for(const mobile of [false,true]){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},locale:'pt-BR',timezoneId:'America/Campo_Grande',isMobile:mobile});
  // Known failure is part of this regression: the scientific panel must stay independent.
  await context.route(/https:\/\/.*open-meteo\.com\//,r=>r.fulfill({status:503,contentType:'application/json',body:'{"error":true,"reason":"offline regression, not meteorological data"}'}));
  const page=await context.newPage(),errors=[],localFailures=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)localFailures.push({url:r.url(),status:r.status()});});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof window.Plotly?.react==='function'&&document.querySelector('#last-updated')?.textContent&&!document.querySelector('#last-updated').textContent.includes('Aguardando'));
  await page.locator('[data-tab="precision"]').click();await page.waitForFunction(()=>document.querySelectorAll('#precision-kpis .agro-kpi').length===4);
  for(const [id,name] of [['navirai','Naviraí'],['diamantino','Diamantino']]){
   await page.locator('#precision-location').selectOption(id);
   assert.match(await page.locator('#precision-provenance').innerText(),new RegExp(name));
   assert.match(await page.locator('#precision-table-body').innerText(),/Sem pares elegíveis/);
   assert.match(await page.locator('#precision-kpis').innerText(),/Não/);
  }
  // Global selector used to remove precision's tbody and leave the previous city on screen.
  await page.locator('#loc-diamantino').click();
  await page.waitForFunction(()=>document.querySelector('#precision-location').value==='diamantino');
  assert.equal(await page.locator('#precision-table-body').count(),1);
  await page.locator('#loc-lat').fill('-20');await page.locator('#loc-lon').fill('-50');
  await page.locator('#loc-form button[type="submit"]').click();
  await page.waitForFunction(()=>document.querySelector('#precision-location').value==='unknown');
  assert.equal(await page.locator('#precision-status').innerText(),'Não há histórico científico validado para esta localidade.');
  assert.equal(await page.locator('#precision-kpis .agro-kpi').count(),0);
  assert.doesNotMatch(await page.locator('#precision-table-body').innerText(),/Naviraí|Diamantino/);
  await page.locator('#precision').screenshot({path:`${output}/unknown_${mobile?'mobile':'desktop'}.png`});
  await page.locator('#loc-navirai').click();
  await page.waitForFunction(()=>document.querySelector('#precision-location').value==='navirai'&&document.querySelectorAll('#precision-kpis .agro-kpi').length===4);
  assert.match(await page.locator('#precision-provenance').innerText(),/Naviraí/);
  await page.locator('#precision').screenshot({path:`${output}/precision_${mobile?'mobile':'desktop'}.png`});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert.equal(overflow,false);
  assert.deepEqual(errors,[]);assert.deepEqual(localFailures,[]);
  report.cases.push({mobile,page_errors:errors,local_loading_errors:localFailures,horizontal_overflow:overflow,localities_separated:true,unknown_locality_clears_prior_results:true,plotly_loaded:true,api_failure_isolation:true});
  await context.close();
 }
 await browser.close();fs.writeFileSync('docs/RELEASES/v22-integration-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exit(1)});
