import * as emnapi from '@emnapi/runtime';

import { env } from 'node:process';
import * as path from 'node:path';

import { assert } from 'chai';

import(path.resolve(env.NODE_PATH, env.NODE_ADDON))
  .then((m) => m.default())
  .then((r) => r.emnapiInit({ context: emnapi.getDefaultContext() }))
  .then((addon) => {
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

    // The Node.js convention calls for a Promise rejection here
    // However SWIG-generated code throws a synchronous exception
    // This an open issue in SWIG JSE: https://github.com/mmomtchev/swig/issues/54
    assert.throws(() => {
      addon.calcAsync('invalid');
    });
  });

