import {chromium} from 'playwright';
const browser=await chromium.launch({executablePath:'/home/rishi/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-webgl','--enable-unsafe-swiftshader']});
try {
 const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 await page.goto('http://localhost:5173',{waitUntil:'networkidle'});
 await page.locator('[data-scene-state="ready"]').waitFor();await page.waitForTimeout(1800);
 console.log(JSON.stringify(await page.evaluate(()=>({touchPoints:navigator.maxTouchPoints,secure:isSecureContext,api:typeof DeviceOrientationEvent,permission:typeof window.DeviceOrientationEvent?.requestPermission,fine:matchMedia('(hover: hover) and (pointer: fine)').matches,reduced:matchMedia('(prefers-reduced-motion: reduce)').matches,scene:{...document.querySelector('.campus-stage').dataset},canvas:{...document.querySelector('canvas').dataset},canvasBounds:document.querySelector('canvas').getBoundingClientRect().toJSON()})),null,2));
 await page.screenshot({path:'artifacts/mobile-preview.png',fullPage:true});
} finally{await browser.close();}
