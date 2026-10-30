/* Real Chromium/Edge rendering against the locally collected public JSON. */
const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.EDGE_EXECUTABLE||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const base=process.env.CAMPO_PREVIEW_URL||'http://127.0.0.1:8776';
 fs.mkdirSync('docs/RELEASES/screenshots',{recursive:true});
 const report={base,checked_at_utc:new Date().toISOString(),cases:[]};
 for(const mobile of [false,true]){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},locale:'pt-BR',timezoneId:'America/Campo_Grande',isMobile:mobile});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#last-updated')?.textContent&&!document.querySelector('#last-updated').textContent.includes('Aguardando'),{timeout:20000});
  const tabs=await page.locator('#tabs button:not([hidden])').evaluateAll(nodes=>nodes.map(n=>n.dataset.tab));
  for(const tab of tabs){
   await page.locator(`#tabs button[data-tab="${tab}"]`).click();
   await page.waitForTimeout(350);
   assert.equal(await page.locator(`#${tab}`).evaluate(el=>el.classList.contains('active')),true);
  }
  await page.locator('#tabs button[data-tab="precision"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#precision-kpis .agro-kpi').length===4,{timeout:15000});
  assert.match(await page.locator('#precision-status').innerText(),/Ainda não há amostras/);
  assert.match(await page.locator('#precision-table-body').innerText(),/Sem pares elegíveis/);
  await page.locator('#precision-location').selectOption('diamantino');
  assert.match(await page.locator('#precision-provenance').innerText(),/Diamantino/);
  await page.locator('#precision-variable').selectOption('precipitation');
  await page.locator('#precision-start').fill('2026-10-01');await page.locator('#precision-end').fill('2026-10-31');
  await page.locator('#precision-location').selectOption('navirai');
  await page.locator('#precision').screenshot({path:`docs/RELEASES/screenshots/precision_${mobile?'mobile':'desktop'}.png`});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert.equal(overflow,false,'Horizontal overflow');
  if(!mobile){
   await page.locator('#tabs button[data-tab="agro"]').click();await page.locator('#agro-operation').selectOption('irrigation');
   assert.doesNotMatch(await page.locator('#agro-kpis').innerText(),/Somente filtros experimentais de pulverização/);
   await page.locator('#agro').screenshot({path:'docs/RELEASES/screenshots/agro_desktop.png'});
   await page.locator('#tabs button[data-tab="maps"]').click();await page.waitForTimeout(1500);
   await page.locator('#maps').screenshot({path:'docs/RELEASES/screenshots/maps_desktop.png'});
  }
  assert.deepEqual(errors,[],'JavaScript page errors');
  report.cases.push({mobile,tabs,js_errors:errors,horizontal_overflow:overflow,precision_empty_state:'verified',locality_filter:'verified'});
  await context.close();
 }
 await browser.close();fs.writeFileSync('docs/RELEASES/v2.2-browser.json',JSON.stringify(report,null,2));
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exit(1)});
