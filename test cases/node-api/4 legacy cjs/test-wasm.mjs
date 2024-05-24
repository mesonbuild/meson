import * as emnapi from '@emnapi/runtime';

import { env } from 'node:process';
import * as path from 'node:path';

import { assert } from 'chai';

import(path.resolve(env.NODE_PATH, env.NODE_ADDON))
  .then((m) => new Promise((resolve, reject) => {
    m.default.onRuntimeInitialized = () => {
      try {
        resolve(m.default.emnapiInit({ context: emnapi.getDefaultContext() }));
      } catch (e) {
        reject(e);
      }
    };
  }))
  .then((addon) => {
    assert.strictEqual(addon.HelloWorld(), 'world');
  });
