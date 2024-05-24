const { env } = require('node:process');
const addon = require(env.NODE_ADDON);
const { assert } = require('chai');

addon.HelloWorld().then((r) => {
  assert.strictEqual(r, 'world');
});
