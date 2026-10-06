import { test } from 'node:test';
import { spawn } from 'node:child_process';
test('landing hero renders across desktop, mobile, reduced motion, and failed model loading', { timeout: 180000 }, async () => {
  await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['scripts/browser-check.mjs'], { stdio: 'inherit' });
    child.on('error', reject);
    child.on('exit', (code) => code === 0 ? resolve() : reject(new Error('Browser check failed: ' + code)));
  });
});
