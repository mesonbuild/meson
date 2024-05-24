import * as emnapi from '@emnapi/runtime';

import { env } from 'node:process';
import * as path from 'node:path';

import { assert } from 'chai';

import(path.resolve(env.NODE_PATH, env.NODE_ADDON))
  .then((m) => m.default())
  .then((r) => r.emnapiInit({ context: emnapi.getDefaultContext() }))
  .then((addon) => addon.HelloWorld())
  .then((r) => {
    assert.strictEqual(r, 'world');
  });
