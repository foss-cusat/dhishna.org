import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, readdirSync, existsSync, rmSync, utimesSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const deployScript = resolve('scripts/deploy-ec2.sh');
// Public key from a throwaway fixture; its private key is not retained.
const hostPublicKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL/h0WdZmOz91Ok98zhgIJpdbRcNA315VBgGM30D8ID8';

// Exercise actual rsync transfers against a temporary directory. SSH is replaced
// with a local transport so these checks never contact a deployment server.
const localSsh = `#!/usr/bin/env node
const fs = require('node:fs');
const {spawnSync} = require('node:child_process');
const args = process.argv.slice(2);
fs.appendFileSync(process.env.DEPLOY_TEST_LOG, JSON.stringify({args, entry: fs.readFileSync(process.env.DEPLOY_TEST_DEST + '/index.html', 'utf8'), assetsArrived: fs.existsSync(process.env.DEPLOY_TEST_DEST + '/assets/new.js')}) + '\\n');
if (args[0] !== '-F' || args[2] !== 'dhishna-deploy') process.exit(90);
const config = fs.readFileSync(args[1], 'utf8');
if (!config.includes('StrictHostKeyChecking yes') || !config.includes('BatchMode yes')) process.exit(91);
const key = config.match(/IdentityFile "([^"]+)"/)[1];
if ((fs.statSync(key).mode & 0o777) !== 0o600) process.exit(92);
if (process.env.EC2_SSH_KEY || process.env.EC2_KNOWN_HOSTS) process.exit(93);
const remote = args.slice(3);
if (remote[0] === 'rsync') {
  if (process.env.DEPLOY_TEST_FAIL_TRANSFER === '1') process.exit(42);
  const command = remote.slice(1).map(value =>
    value === '/var/www/dhishna.org/' ? process.env.DEPLOY_TEST_DEST + '/' : value);
  const result = spawnSync('/usr/bin/rsync', command, {stdio: 'inherit'});
  process.exit(result.status ?? 94);
}
if (!remote[0]?.includes("test -w '/var/www/dhishna.org'")) process.exit(95);
process.exit(process.env.DEPLOY_TEST_FAIL_PREFLIGHT === '1' ? 43 : 0);
`;

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'dhishna deploy test-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  for (const folder of ['bin', 'credentials', 'dist/assets', 'dist/models', 'dist/.git', 'live/assets', 'live/.well-known']) {
    mkdirSync(join(root, folder), {recursive: true});
  }
  writeFileSync(join(root, 'bin/ssh'), localSsh, {mode: 0o755});
  for (const [name, content] of Object.entries({
    'dist/index.html': 'new-entry',
    'dist/models/cusat.glb': 'desktop model',
    'dist/models/cusat-mobile.glb': 'mobile model',
    'dist/campus-poster.webp': 'poster',
    'dist/assets/new.js': 'new script',
    'dist/.git/config': 'must stay local',
    'live/index.html': 'old-entry',
    'live/assets/old.js': 'old script',
    'live/.well-known/sentinel': 'keep server files',
  })) writeFileSync(join(root, name), content);
  // Matching sizes/timestamps should still upload changed contents.
  for (const name of ['dist/index.html', 'live/index.html']) {
    utimesSync(join(root, name), 1700000000, 1700000000);
  }
  const env = {
    ...process.env,
    PATH: join(root, 'bin') + ':' + process.env.PATH,
    RUNNER_TEMP: join(root, 'credentials'),
    EC2_HOST: 'example.invalid',
    EC2_USER: 'deploy',
    EC2_PORT: '2222',
    EC2_SSH_KEY: 'test key',
    EC2_KNOWN_HOSTS: `[example.invalid]:2222 ${hostPublicKey}`,
    DEPLOY_TEST_LOG: join(root, 'transport.log'),
    DEPLOY_TEST_DEST: join(root, 'live'),
  };
  return {
    root,
    run: (overrides = {}) => spawnSync('bash', [deployScript], {
      cwd: root, env: {...env, ...overrides}, encoding: 'utf8', timeout: 15000,
    }),
    read: (name) => readFileSync(join(root, name), 'utf8'),
    connections: () => existsSync(env.DEPLOY_TEST_LOG)
      ? readFileSync(env.DEPLOY_TEST_LOG, 'utf8').trim().split('\n').map(line => JSON.parse(line)) : [],
    checkCleanup: () => assert.deepEqual(readdirSync(env.RUNNER_TEMP), [], 'Temporary SSH credentials are removed'),
  };
}

test('deploy uploads built files, publishes the entry page, and retains existing assets', (t) => {
  const f = fixture(t);
  const result = f.run();
  assert.equal(result.status, 0, result.stderr);
  assert.equal(f.read('live/index.html'), 'new-entry');
  assert.equal(f.read('live/models/cusat-mobile.glb'), 'mobile model');
  assert.equal(f.read('live/assets/new.js'), 'new script');
  assert.equal(f.read('live/assets/old.js'), 'old script');
  assert.equal(f.read('live/.well-known/sentinel'), 'keep server files');
  assert(!existsSync(join(f.root, 'live/.git')));
  const connections = f.connections();
  assert.equal(connections.length, 3, 'Preflight, assets, then entry page');
  assert.equal(connections[2].entry, 'old-entry', 'Previous page remains until the final transfer');
  assert.equal(connections[2].assetsArrived, true, 'New assets arrive before publishing the entry page');
  assert.equal(statSync(join(f.root, 'live/index.html')).mode & 0o777, 0o644, 'Web server can read uploaded files');
  f.checkCleanup();
});

test('failed asset upload leaves the previous entry page and cleans up the SSH key', (t) => {
  const f = fixture(t);
  const result = f.run({DEPLOY_TEST_FAIL_TRANSFER: '1'});
  assert.notEqual(result.status, 0);
  assert.equal(f.read('live/index.html'), 'old-entry');
  assert.equal(f.connections().length, 2, 'Entry-page upload is never started');
  f.checkCleanup();
});

test('failed server preflight prevents all file transfers', (t) => {
  const f = fixture(t);
  assert.notEqual(f.run({DEPLOY_TEST_FAIL_PREFLIGHT: '1'}).status, 0);
  assert.equal(f.connections().length, 1);
  assert.equal(f.read('live/index.html'), 'old-entry');
  f.checkCleanup();
});

test('missing secrets, invalid SSH configuration, and incomplete builds fail before connecting', (t) => {
  const f = fixture(t);
  for (const overrides of [
    {EC2_SSH_KEY: ''}, {EC2_KNOWN_HOSTS: ''}, {EC2_HOST: 'host\nProxyCommand bad'},
    {EC2_USER: '-root'}, {EC2_PORT: '0'}, {EC2_PORT: '70000'},
  ]) assert.notEqual(f.run(overrides).status, 0);
  rmSync(join(f.root, 'dist/models/cusat-mobile.glb'));
  assert.notEqual(f.run().status, 0);
  assert.equal(f.connections().length, 0);
  f.checkCleanup();
});

test('host-key entries for a different host or port fail before connecting', (t) => {
  const f = fixture(t);
  for (const entry of [
    `[other.invalid]:2222 ${hostPublicKey}`,
    `[example.invalid]:22 ${hostPublicKey}`,
    `example.invalid ${hostPublicKey}`,
    hostPublicKey,
    `"[example.invalid]:2222 ${hostPublicKey}"`,
  ]) {
    const result = f.run({EC2_KNOWN_HOSTS: entry});
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /EC2_KNOWN_HOSTS has no entry matching EC2_HOST and EC2_PORT/);
    assert.match(result.stderr, /Expected entry format: \[example\.invalid\]:2222/);
    assert.equal(f.connections().length, 0);
    assert.equal(f.read('live/index.html'), 'old-entry');
    f.checkCleanup();
  }
});

test('a fingerprint or malformed public key fails before connecting', (t) => {
  const f = fixture(t);
  for (const key of ['SHA256:not-a-public-key', 'truncated-key']) {
    const result = f.run({EC2_KNOWN_HOSTS: `[example.invalid]:2222 ssh-ed25519 ${key}`});
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /EC2_KNOWN_HOSTS.*no valid public key/);
    assert.equal(f.connections().length, 0);
    assert.equal(f.read('live/index.html'), 'old-entry');
    f.checkCleanup();
  }
});

test('default and zero-padded ports use the canonical OpenSSH host lookup', (t) => {
  const f = fixture(t);
  for (const [port, host] of [
    ['', 'example.invalid'], ['22', 'example.invalid'],
    ['00022', 'example.invalid'], ['02222', '[example.invalid]:2222'],
  ]) {
    const result = f.run({EC2_PORT: port, EC2_KNOWN_HOSTS: `${host} ${hostPublicKey}`});
    assert.equal(result.status, 0, result.stderr);
    assert.equal(f.read('live/index.html'), 'new-entry');
    f.checkCleanup();
  }
});

test('verified hashed host-key entries and Windows line endings are accepted', (t) => {
  const f = fixture(t);
  const knownHosts = join(f.root, 'hashed_hosts');
  writeFileSync(knownHosts, `[example.invalid]:2222 ${hostPublicKey}\n`);
  const hash = spawnSync('ssh-keygen', ['-H', '-f', knownHosts], {encoding: 'utf8'});
  assert.equal(hash.status, 0, hash.stderr);
  const entry = readFileSync(knownHosts, 'utf8');
  assert(entry.startsWith('|1|'), 'The fixture uses a hashed hostname');
  const result = f.run({EC2_KNOWN_HOSTS: entry.replaceAll('\n', '\r\n')});
  assert.equal(result.status, 0, result.stderr);
  assert.equal(f.read('live/index.html'), 'new-entry');
  f.checkCleanup();
});
