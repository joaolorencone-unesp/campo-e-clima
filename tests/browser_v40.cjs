/* Real Chromium rendering of the v4 interface against locally replayed/preview JSON (no live weather API).
 * Screenshots under docs/RELEASES/v4 and a JSON report; exits non-zero on page errors, overflow or missing panels. */
const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const base=process.env.CAMPO_PREVIEW_URL||'http://127.0.0.1:8777';
 const out='docs/RELEASES/v4';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const report={base,checked_at_utc:new Date().toISOString(),cases:[]};
 for(const mobile of [false,true]){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},deviceScaleFactor:mobile?2:1,locale:'pt-BR',timezoneId:'America/Campo_Grande',isMobile:mobile});
  await context.route(/^https?:\/\/(?!127\.0\.0\.1)/,route=>route.abort()); // offline: no OSM/NASA/Open-Meteo
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/?modo=simples',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#weekly-board table.board')!==null&&document.querySelector('#farm-summary .farm-cards')!==null,{timeout:20000});
  const tag=mobile?'mobile':'desktop';
  // brand + simple mode
  assert.equal(await page.evaluate(()=>document.body.classList.contains('mode-simple')),true);
  assert.equal(await page.locator('#tabs button[data-tab="maps"]').evaluate(el=>el.hidden),true,'maps hidden in simple mode');
  assert.equal(await page.locator('#tabs button[data-tab="observations"]').evaluate(el=>el.hidden),false);
  const logoVisible=await page.locator(mobile?'.brand-logo-icon':'.brand-logo').isVisible();assert.equal(logoVisible,true,'brand logo visible');
  const weeklyRows=await page.locator('#weekly-board tr.board-row').count();assert.ok(weeklyRows>=5,'weekly rows '+weeklyRows);
  const weeksRows=await page.locator('#weeks-ahead tbody tr').count();assert.ok(weeksRows>=2,'weeks ahead rows');
  const bulletinHidden=await page.locator('#bulletin-card').evaluate(el=>el.hidden);
  const bulletinText=bulletinHidden?'':await page.locator('#bulletin-text').innerText();
  const stationCardHidden=await page.locator('#station-overview-card').evaluate(el=>el.hidden);
  await page.screenshot({path:`${out}/overview_simple_${tag}.png`,fullPage:false});
  await page.locator('#weekly-board-panel').screenshot({path:`${out}/weekly_board_${tag}.png`});
  await page.locator('#weeks-ahead-panel').screenshot({path:`${out}/weeks_ahead_${tag}.png`});
  // expand a weekly row (3-hourly detail)
  await page.locator('#weekly-board tr.board-row').nth(1).click();await page.waitForTimeout(150);
  assert.equal(await page.locator('#weekly-board tr.board-detail').nth(1).evaluate(el=>el.hidden),false,'detail row opens');
  if(!bulletinHidden)await page.locator('#bulletin-card').screenshot({path:`${out}/bulletin_${tag}.png`});
  if(!stationCardHidden)await page.locator('#station-overview-card').screenshot({path:`${out}/station_overview_${tag}.png`});
  // observations: station panel
  await page.locator('#tabs button[data-tab="observations"]').click();
  await page.waitForFunction(()=>document.querySelector('#stations-body table')!==null,{timeout:15000});
  const stationTabs=await page.locator('#stations-tabs button').count();assert.ok(stationTabs>=1,'station tabs');
  assert.match(await page.locator('#station-matrix').innerText(),/D1/);
  await page.locator('#stations-panel').screenshot({path:`${out}/stations_${tag}.png`});
  await page.locator('#station-variable').selectOption('rain_mm');await page.waitForTimeout(100);
  assert.match(await page.locator('#station-matrix').innerText(),/viés/);
  // advanced mode: maps with GOES control, precision with model comparison
  await page.locator('#mode-switch button[data-mode="advanced"]').click();await page.waitForTimeout(200);
  await page.locator('#tabs button[data-tab="maps"]').click();await page.waitForTimeout(500);
  await page.locator('#map-satellite').selectOption('GOES-East_ABI_GeoColor');await page.waitForTimeout(400);
  assert.equal(await page.locator('#goes-control').evaluate(el=>el.hidden),false,'GOES control shown');
  assert.match(await page.locator('#goes-time').innerText(),/UTC/);
  if(!mobile)await page.screenshot({path:`${out}/maps_goes_desktop.png`,fullPage:false});
  await page.locator('#tabs button[data-tab="precision"]').click();await page.waitForTimeout(700);
  const compareRows=await page.locator('#models-compare-table tbody tr').count();
  if(compareRows)await page.locator('#models-compare-panel').screenshot({path:`${out}/models_compare_${tag}.png`});
  await page.locator('#tabs button[data-tab="overview"]').click();await page.waitForTimeout(400);
  if(!mobile)await page.screenshot({path:`${out}/overview_advanced_desktop.png`,fullPage:false});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
  assert.equal(overflow,false,'horizontal overflow');
  assert.deepEqual(errors,[],'JavaScript page errors');
  report.cases.push({mobile,weekly_rows:weeklyRows,weeks_rows:weeksRows,bulletin:bulletinText.slice(0,120),station_card:!stationCardHidden,station_tabs:stationTabs,compare_rows:compareRows,js_errors:errors,horizontal_overflow:overflow});
  await context.close();
 }
 await browser.close();fs.writeFileSync(`${out}/browser_report.json`,JSON.stringify(report,null,2));console.log(JSON.stringify(report.cases));
})().catch(e=>{console.error(e);process.exit(1)});
