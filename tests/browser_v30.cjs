/* Real Chromium rendering of the v3 interface against locally replayed JSON (no live weather API).
 * Produces screenshots under docs/RELEASES/v3 and a JSON report; exits non-zero on page errors or overflow. */
const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const base=process.env.CAMPO_PREVIEW_URL||'http://127.0.0.1:8777';
 const out='docs/RELEASES/v3';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const report={base,checked_at_utc:new Date().toISOString(),cases:[]};
 for(const mobile of [false,true]){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},deviceScaleFactor:mobile?2:1,locale:'pt-BR',timezoneId:'America/Campo_Grande',isMobile:mobile});
  // Block third-party hosts: offline validation must not depend on OSM/NASA/Open-Meteo availability.
  await context.route(/^https?:\/\/(?!127\.0\.0\.1)/,route=>route.abort());
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/?modo=simples',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#farm-summary .farm-cards')!==null,{timeout:20000});
  const tag=mobile?'mobile':'desktop';
  assert.equal(await page.evaluate(()=>document.body.classList.contains('mode-simple')),true,'simple mode default');
  assert.equal(await page.locator('#tabs button[data-tab="precision"]').evaluate(el=>el.hidden),true,'science tabs hidden in simple mode');
  const simpleCards=await page.locator('#farm-summary .farm-card').count();assert.equal(simpleCards,6);
  const headline=await page.locator('#farm-summary h2').innerText();assert.ok(headline.length>10);
  await page.screenshot({path:`${out}/overview_simple_${tag}.png`,fullPage:false});
  await page.locator('#farm-summary').screenshot({path:`${out}/farm_summary_${tag}.png`});
  // advanced mode: every visible tab opens
  await page.locator('#mode-switch button[data-mode="advanced"]').click();
  await page.waitForTimeout(200);
  assert.equal(await page.evaluate(()=>document.body.classList.contains('mode-advanced')),true);
  const tabs=await page.locator('#tabs button:not([hidden])').evaluateAll(nodes=>nodes.map(n=>n.dataset.tab));
  assert.ok(tabs.includes('precision')&&tabs.includes('verification'));
  for(const tab of tabs){await page.locator(`#tabs button[data-tab="${tab}"]`).click();await page.waitForTimeout(250);
   assert.equal(await page.locator(`#${tab}`).evaluate(el=>el.classList.contains('active')),true,tab);}
  await page.locator('#tabs button[data-tab="rain"]').click();await page.waitForTimeout(600);
  assert.match(await page.locator('#rain-accumulated-body').innerText(),/dias/);
  assert.match(await page.locator('#rain-agreement-daily').innerText(),/de 8|de \d/);
  assert.match(await page.locator('#rain-hour-resolution-note').innerText(),/Passo nativo/);
  await page.locator('#rain-accumulated-panel').screenshot({path:`${out}/rain_accumulated_${tag}.png`});
  if(!mobile){await page.screenshot({path:`${out}/rain_advanced_desktop.png`,fullPage:false});}
  await page.locator('#tabs button[data-tab="verification"]').click();await page.waitForTimeout(600);
  assert.match(await page.locator('#freshness-body').innerText(),/ECMWF IFS/);
  await page.locator('#freshness-panel').screenshot({path:`${out}/freshness_${tag}.png`});
  await page.locator('#tabs button[data-tab="agro"]').click();await page.waitForTimeout(700);
  if(!mobile)await page.screenshot({path:`${out}/agro_desktop.png`,fullPage:false});
  await page.locator('#tabs button[data-tab="overview"]').click();await page.waitForTimeout(400);
  await page.screenshot({path:`${out}/overview_advanced_${tag}.png`,fullPage:false});
  assert.match(await page.locator('#agro-ensemble-panel').innerText(),/mesmo membro/);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
  assert.equal(overflow,false,'horizontal overflow');
  assert.deepEqual(errors,[],'JavaScript page errors');
  report.cases.push({mobile,tabs,js_errors:errors,horizontal_overflow:overflow,simple_cards:simpleCards,headline});
  await context.close();
 }
 await browser.close();fs.writeFileSync(`${out}/browser_report.json`,JSON.stringify(report,null,2));console.log(JSON.stringify(report.cases.map(c=>({mobile:c.mobile,tabs:c.tabs.length,headline:c.headline})))); 
})().catch(e=>{console.error(e);process.exit(1)});
