import {copyFile} from 'node:fs/promises';
import {chromium} from 'playwright';
const browser=await chromium.launch({executablePath:'/home/rishi/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-webgl','--enable-unsafe-swiftshader']});
try {
 const page=await browser.newPage({viewport:{width:1400,height:875},deviceScaleFactor:1,reducedMotion:'reduce'});
 page.on('pageerror',e=>console.error(e));
 await page.goto('http://localhost:5173',{waitUntil:'networkidle'});
 await page.locator('[data-scene-state="ready"]').waitFor({timeout:45000});
 await page.screenshot({path:'artifacts/colour-match/website-after.png'});
 await page.addStyleTag({content:'.campus-stage{position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;mask-image:none!important;-webkit-mask-image:none!important}.header,.hero-copy,.footer,.scene-caption,.scene-blend{visibility:hidden!important}'});
 await page.waitForTimeout(1000);
 await page.screenshot({path:'artifacts/colour-match/scene-after.png'});
 if (process.argv.includes('--poster')) await copyFile('artifacts/colour-match/scene-after.png', 'public/campus-poster.png');
 console.log('Captured corrected website and unmasked scene.');
} finally {await browser.close();}
