import * as emnapi from '@emnapi/runtime';

import { env } from 'node:process';
import * as path from 'node:path';

import { assert } from 'chai';

const AsyncFunction = (async () => { }).constructor;

import(path.resolve(env.NODE_PATH, env.NODE_ADDON))
  .then((m) => {
    const r = m.default;
    if (r instanceof AsyncFunction)
      throw new Error('This is not a Node.js-exclusive loader');
    return r();
  })
  .then((r) => r.emnapiInit({ context: emnapi.getDefaultContext() }))
  .then((addon) => {
    assert.strictEqual(addon.HelloWorld(), 'world');
  });

