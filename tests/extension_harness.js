// Runs the real extension/content.js in a small fake browser and prints the
// payload of one window. Used by tests/test_extension_parity.py.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const events = JSON.parse(fs.readFileSync(0, 'utf8'));
let now = 0;
let payload = null;
const storage = new Map();
const sandbox = {
  console,
  crypto: require('crypto').webcrypto,
  performance: { now: () => now },
  window: { location: { origin: 'http://test.invalid' }, addEventListener() {} },
  document: { getElementById: () => null, documentElement: null, readyState: 'complete', addEventListener() {} },
  sessionStorage: { getItem: (key) => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) },
  chrome: { runtime: { sendMessage: (message) => { payload = message.payload; return Promise.resolve({ ok: true }); } } },
  MutationObserver: class { observe() {} disconnect() {} },
};
vm.createContext(sandbox);
const extension = path.join(__dirname, '..', 'extension');
for (const file of ['features.js', 'content.js']) {
  vm.runInContext(fs.readFileSync(path.join(extension, file), 'utf8'), sandbox, { filename: file });
}
for (const event of events) {
  now = event.t;
  if (event.type === 'move') sandbox.onMouseMove({ clientX: event.x, clientY: event.y });
  else if (event.type === 'click') sandbox.onClick();
  else if (event.type === 'right') sandbox.onMouseDown({ button: 2 });
  else if (event.type === 'down') sandbox.onKeyDown({ code: event.code, repeat: false });
  else if (event.type === 'up') sandbox.onKeyUp({ code: event.code });
}
sandbox.sendWindowFeatures();
process.stdout.write(JSON.stringify(payload));
