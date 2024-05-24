const { env } = require('node:process');
const addon = require(env.NODE_ADDON);
const { assert } = require('chai');

assert.strictEqual(addon.HelloWorld(), 'Hello C World');
