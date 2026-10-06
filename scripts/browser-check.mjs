import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { setTimeout as delay } from 'node:timers/promises';

const browserPath = process.env.BROWSER_PATH || [
  '/home/rishi/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',
  '/home/rishi/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome',
].find(existsSync);
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', '4177', '--strictPort'], {
  stdio: ['ignore', 'pipe', 'pipe'],
});
let serverLog = '';
server.stdout.on('data', (data) => { serverLog += data; });
server.stderr.on('data', (data) => { serverLog += data; });
let browser;
const reports = [];
mkdirSync('artifacts', { recursive: true });

async function dispatchTilt(page,beta,gamma) {
  await page.evaluate(({beta,gamma})=>{
    const event=new Event('deviceorientation');
    Object.defineProperties(event,{beta:{value:beta},gamma:{value:gamma}});
    window.dispatchEvent(event);
  },{beta,gamma});
}
async function mockTiltPermission(page,permission) {
  await page.addInitScript((permission)=>{
    window.tiltPermissionRequests=0;
    class OrientationEvent extends Event {
      static requestPermission(){window.tiltPermissionRequests++;return Promise.resolve(permission);}
    }
    Object.defineProperty(window,'DeviceOrientationEvent',{configurable:true,value:OrientationEvent});
  },permission);
}

async function pageReady(page, state = 'ready') {
  await page.goto('http://127.0.0.1:4177', { waitUntil: 'networkidle' });
  await page.locator('[data-scene-state="' + state + '"]').waitFor({ timeout: 30000 });
  await page.evaluate(() => document.fonts.ready);
  await delay(1400);
}
async function audit(page, label) {
  const metrics = await page.evaluate(() => ({
    viewport: [innerWidth, innerHeight],
    scrollWidth: document.documentElement.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
    scrollY,
    fixedLayout: document.querySelector('.landing').dataset.mobileLayout === 'true',
    compact: matchMedia('(max-width:700px), (max-width:1100px) and (max-height:600px), (pointer:coarse)').matches,
    copy: document.querySelector('.hero-copy').getBoundingClientRect().toJSON(),
    date: document.querySelector('.date-location').getBoundingClientRect().toJSON(),
    footerDisplay: getComputedStyle(document.querySelector('.footer')).display,
    heading: document.querySelector('h1').getBoundingClientRect().toJSON(),
    scene: document.querySelector('.campus-stage').getBoundingClientRect().toJSON(),
    status: document.querySelector('.campus-stage').getAttribute('data-scene-state'),
    renderer: {...document.querySelector('canvas')?.dataset},
    imagesLoaded: [...document.images].every((img) => img.complete && img.naturalWidth > 0),
  }));
  assert(metrics.scrollWidth <= metrics.viewport[0], 'No horizontal overflow: ' + label);
  assert(metrics.heading.x >= 0 && metrics.heading.right <= metrics.viewport[0], 'Heading visible: ' + label);
  assert(metrics.imagesLoaded, 'Fallback image loaded: ' + label);
  if (metrics.fixedLayout) {
    assert(metrics.scrollHeight<=metrics.viewport[1]+1,'Phone fits one screen: '+label);
    assert(metrics.date.bottom<=metrics.viewport[1] && metrics.heading.y>=0,'Phone copy stays visible: '+label);
    if (metrics.viewport[0]>metrics.viewport[1]) {
      assert(metrics.heading.right<=metrics.viewport[0]*.5,'Landscape copy fits beside the campus: '+label);
    } else {
      assert(metrics.copy.bottom<=metrics.scene.top+1,'Portrait copy fits above the campus: '+label);
    }
    await page.evaluate(()=>scrollTo(0,1000));
    assert.equal(await page.evaluate(()=>scrollY),0,'Phone page cannot scroll: '+label);
    assert.equal(metrics.footerDisplay,'none','Mobile footer has no white strip: '+label);
    assert(Math.abs(metrics.scene.bottom+metrics.scrollY-metrics.scrollHeight)<=2,'Campus reaches the bottom of the page: '+label);
  }
  if (metrics.status === 'ready') {
    assert.equal(metrics.renderer.gpuWind,'rooted');
    assert.equal(metrics.renderer.profile,metrics.compact ? 'mobile' : 'desktop');
    assert(Number(metrics.renderer.cameraWidth)<120,'Camera keeps campus framed after initial sizing: '+label);
    assert(Number(metrics.renderer.drawCalls) < 140,'Renderer draw calls: '+label);
  }
  reports.push({ label, ...metrics });
}
try {
  for (let i = 0; i < 100; i++) {
    if (server.exitCode !== null) throw new Error('Vite failed: ' + serverLog);
    try { if ((await fetch('http://127.0.0.1:4177')).ok) break; } catch {}
    await delay(100);
  }
  browser = await chromium.launch({
    executablePath: browserPath,
    headless: true,
    args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-webgl', '--enable-unsafe-swiftshader'],
  });
  const errors = [];
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on('pageerror', (error) => errors.push(error.message));
  await pageReady(page);
  await audit(page, 'desktop');
  await page.screenshot({ path: 'artifacts/desktop.png' });
  const windA = await page.screenshot({ clip:{x:650,y:180,width:700,height:500} });
  await delay(1000);
  const windB = await page.screenshot({ clip:{x:650,y:180,width:700,height:500} });
  assert(!windA.equals(windB),'GPU wind changes the scene while the pointer stays fixed');
  const frames = await page.evaluate(() => new Promise((resolve) => {
    let count = 0; const start = performance.now();
    function frame(now) {
      count++;
      if (now - start >= 1500) resolve({ fps: Math.round(count * 1000 / (now - start)), mode: 'headless desktop / software WebGL' });
      else requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }));
  reports.push({ label: 'render-scheduling', ...frames });
  const renderStart=await page.locator('canvas').getAttribute('data-frames');
  const renderTime=Date.now();await delay(4000);
  const renderEnd=await page.locator('canvas').getAttribute('data-frames');
  reports.push({label:'actual-scene-frames',fps:Number(((Number(renderEnd)-Number(renderStart))*1000/(Date.now()-renderTime)).toFixed(1)),mode:'headless software WebGL; not physical-device certification'});
  // Simulate a visibility change to verify our listener and demand-rendering behavior.
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await delay(600);
  const hiddenA = await page.screenshot({ clip: { x: 650, y: 120, width: 700, height: 600 } });
  await page.mouse.move(700, 200);
  await delay(400);
  const hiddenB = await page.screenshot({ clip: { x: 650, y: 120, width: 700, height: 600 } });
  assert(hiddenA.equals(hiddenB), 'Visibility listener freezes scene rendering');
  await page.evaluate(() => {
    delete document.hidden;
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await page.setViewportSize({ width: 1024, height: 768 });
  await delay(500);
  await audit(page, 'tablet-landscape');
  await page.screenshot({ path: 'artifacts/tablet.png' });
  await context.close();

  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
    isMobile: true, hasTouch: true,
  });
  const mp = await mobile.newPage();
  const mobileModels=[];mp.on('request',r=>{if(r.url().includes('/models/'))mobileModels.push(r.url());});
  mp.on('pageerror', (error) => errors.push(error.message));
  await pageReady(mp);
  await audit(mp, 'mobile');
  assert(mobileModels.some(url=>url.includes('cusat-mobile.glb')));
  assert(!mobileModels.some(url=>url.includes('/cusat.glb')),'Phone avoids downloading the desktop scene');
  await mp.screenshot({ path: 'artifacts/mobile.png', fullPage: true });
  for (const [width,height,label] of [[412,915,'phone-412x915'],[412,780,'phone-browser-bars'],[320,568,'compact-phone'],[915,412,'phone-landscape'],[568,320,'small-phone-landscape']]) {
    await mp.setViewportSize({width,height});await delay(500);await audit(mp,label);
    await mp.screenshot({path:'artifacts/'+label+'.png'});
  }
  await mp.setViewportSize({width:390,height:1200});
  await delay(500);await audit(mp,'tall-mobile');
  await mp.screenshot({path:'artifacts/mobile-tall.png',fullPage:true});
  await mp.setViewportSize({ width: 360, height: 740 });
  await delay(400);
  await audit(mp, 'small-mobile');
  await mp.screenshot({ path: 'artifacts/mobile-small.png', fullPage: true });
  // Browsers without a permission API start listening automatically.
  await mp.locator('[data-tilt-state="listening"]').waitFor();
  const cameraBefore=Number(await mp.locator('canvas').getAttribute('data-camera-x'));
  await dispatchTilt(mp,45,0);await dispatchTilt(mp,63,18);
  await mp.waitForFunction((start)=>Number(document.querySelector('canvas').dataset.cameraX)>start+.2,cameraBefore,{timeout:10000});
  const cameraAfter=Number(await mp.locator('canvas').getAttribute('data-camera-x'));
  assert(cameraAfter<=35.801,'Phone camera travel stays bounded');
  reports.push({label:'phone-tilt',before:cameraBefore,after:cameraAfter});
  await mp.locator('.campus-stage').evaluate(el=>el.style.transform='translateY(200vh)');
  await delay(1200);
  const offscreenA=await mp.locator('canvas').getAttribute('data-frames');
  await delay(1400);
  const offscreenB=await mp.locator('canvas').getAttribute('data-frames');
  assert.equal(offscreenA,offscreenB,'Offscreen mobile scene stops scheduling frames');
  reports.push({label:'offscreen-scene',passed:true});
  await mobile.close();

  const reduced = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const rp = await reduced.newPage();
  rp.on('pageerror', (error) => errors.push(error.message));
  await pageReady(rp);
  assert.equal(await rp.getByRole('button', { name: /scene motion/ }).count(), 0, 'Scene motion control is absent');
  const reducedA = await rp.screenshot({ clip: { x: 650, y: 120, width: 700, height: 600 } });
  await rp.mouse.move(1200, 600);
  await delay(400);
  const reducedB = await rp.screenshot({ clip: { x: 650, y: 120, width: 700, height: 600 } });
  assert(reducedA.equals(reducedB), 'Reduced-motion scene stays still');
  await audit(rp, 'reduced-motion');
  await reduced.close();

  const fallback = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const fp = await fallback.newPage();
  // Failed model loading must reveal the poster without hiding the landing content.
  await fp.route('**/models/cusat*.glb*', (route) => route.abort());
  await pageReady(fp, 'fallback');
  await audit(fp, 'model-load-fallback');
  assert(await fp.getByRole('heading', { name: /Something's brewing/ }).isVisible());
  await fp.screenshot({ path: 'artifacts/fallback.png', fullPage: true });
  await fallback.close();
  const unsupported = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const up = await unsupported.newPage();
  await up.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, ...args) {
      if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') return null;
      return original.call(this, type, ...args);
    };
  });
  await pageReady(up, 'fallback');
  await audit(up, 'unsupported-webgl-fallback');
  await unsupported.close();
  const saver=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const sp=await saver.newPage();const saverRequests=[];
  sp.on('request',r=>saverRequests.push(r.url()));
  await sp.addInitScript(()=>Object.defineProperty(navigator,'connection',{configurable:true,value:{saveData:true}}));
  await pageReady(sp,'fallback');
  assert(!saverRequests.some(url=>url.includes('/models/')),'Data saver skips the model download');
  assert.equal(await sp.getByRole('button',{name:/scene motion/}).count(),0);
  await audit(sp,'data-saver-fallback');await saver.close();
  const lost=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const lp=await lost.newPage();await pageReady(lp);
  await lp.locator('canvas').evaluate(canvas=>canvas.dispatchEvent(new Event('webglcontextlost')));
  await lp.locator('[data-scene-state=\"fallback\"]').waitFor();
  await audit(lp,'context-lost-fallback');await lost.close();
  // iOS-style permissions: no automatic prompt; grant is requested only on tap.
  const tiltAllowed=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const tp=await tiltAllowed.newPage();tp.on('pageerror',e=>errors.push(e.message));
  await mockTiltPermission(tp,'granted');await pageReady(tp);
  assert.equal(await tp.evaluate(()=>window.tiltPermissionRequests),0);
  await tp.getByRole('button',{name:'Enable tilt'}).click();
  await tp.locator('[data-tilt-state="listening"]').waitFor();
  assert.equal(await tp.evaluate(()=>window.tiltPermissionRequests),1);
  const start=Number(await tp.locator('canvas').getAttribute('data-camera-x'));
  await dispatchTilt(tp,null,null);await dispatchTilt(tp,50,2);await dispatchTilt(tp,50,20);
  await tp.waitForFunction((start)=>Number(document.querySelector('canvas').dataset.cameraX)>start+.2,start,{timeout:10000});
  await tp.emulateMedia({reducedMotion:'reduce'});
  await tp.locator('[data-tilt-state="off"]').waitFor();await delay(500);
  const stillA=await tp.screenshot();await dispatchTilt(tp,-60,-50);await delay(500);
  assert(stillA.equals(await tp.screenshot()),'Reduced motion freezes the camera even with sensor events');
  reports.push({label:'phone-tilt-permission-and-reduced-motion',passed:true});await tiltAllowed.close();

  const tiltDenied=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const dp=await tiltDenied.newPage();dp.on('pageerror',e=>errors.push(e.message));
  await mockTiltPermission(dp,'denied');await pageReady(dp);
  await dp.getByRole('button',{name:'Enable tilt'}).click();
  await dp.locator('[data-tilt-state="denied"]').waitFor();
  const deniedStart=await dp.locator('canvas').getAttribute('data-camera-x');
  await dispatchTilt(dp,40,0);await dispatchTilt(dp,60,18);await delay(1200);
  assert.equal(await dp.locator('canvas').getAttribute('data-camera-x'),deniedStart);
  assert(await dp.getByRole('status').isVisible());
  reports.push({label:'phone-tilt-permission-denied',passed:true});await tiltDenied.close();
  assert.deepEqual(errors, [], 'No unhandled runtime errors');
  writeFileSync('artifacts/browser-report.json', JSON.stringify({ passed: true, reports }, null, 2));
  console.log('Browser checks passed: ' + reports.map((report) => report.label).join(', '));
} finally {
  await browser?.close();
  server.kill('SIGTERM');
}
