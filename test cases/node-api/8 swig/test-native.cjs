const { env } = require('node:process');
const addon = require(env.NODE_ADDON);
const { assert } = require('chai');

const pi = new addon.Pi(1e6);

// Call the sync method
assert.closeTo(pi.approxSync(), Math.PI, 1e-5);

// Call the async method
pi.approxAsync().then((r) => {
  assert.closeTo(r, Math.PI, 1e-5);
});

// Call the global sync function
assert.closeTo(addon.calcSync(pi)[1], Math.PI, 1e-5);

// Call the global async function
addon.calcAsync(pi).then((r) => {
  assert.closeTo(r[1], Math.PI, 1e-5);
});

// Call the handwritten %native async wrapper
addon.piAsync(pi).then((r) => {
  assert.closeTo(r, Math.PI, 1e-5);
});

// Exception handling
assert.throws(() => {
  addon.calcSync('invalid');
});

// The Node.js convention calls for a Promise rejection here
// However SWIG-generated code throws a synchronous exception
// This an open issue in SWIG JSE: https://github.com/mmomtchev/swig/issues/54
assert.throws(() => {
  addon.calcAsync('invalid');
});
