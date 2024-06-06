A quickstart by example:

```python
project(
  'Hello World for meson',
  # Not mandatory, but this is the default when using node-gyp
  # (in meson, the default is buildtype=debug)
  default_options: ['buildtype=release'],
  ['c', 'cpp']
)

# Simply include the module
napi = import('node-api')

# Get the state of --enable-option1 or --disable-option1 from 'npm install --enable-option1'
# option must be declared as a boolean option in meson.options
# This is not an officially documented `npm` feature but it is widely used by the
# existing build systems and it is expected to always work
if get_option('option1')
  add_global_arguments('-DOPTION1', language: 'cpp')
endif

# Get the value of --option2=value from 'npm install --option2=value'
# option must be declared as a string option in meson.options
# Use extreme caution as this is not an officially documented `npm` feature
# and some option names can be interpreted by `npm` itself
if get_option('option2')
  add_global_arguments('-DOPTION2=' + get_option('option2'), language: 'cpp')
endif

# Use napi.extension_module() instead of
# shared_module() with the same arguments
addon = napi.extension_module(
  # The name of the addon
  'example_addon',
  # The sources
  [ 'src/example_main.cc' ],
  # Will install to the location specified by -Dprefix=...
  # (usually ./lib/binding/{platform}-{arch})
  install: true
  )

# There is a very basic built-in test runner
# It will receive the path to the addon in NODE_PATH and
# the name of the shared object in NODE_ADDON
if host_machine.system() == 'emscripten'
  napi.test('example_test', 'test-wasm.mjs', addon)
else
  napi.test('example_test', 'test-native.cjs', addon)
endif
```

The project must have a root `package.json` and `node` must be installed and available in the `PATH`.

The default build is the native build.

In order to build to WASM, `emscripten` must be installed and activated in the environment. The bare minimum for the `meson` `cross-file` is:

```ini
[binaries]
c = 'emcc'
cpp = 'em++'
ar = 'emar'
strip = 'emstrip'

[host_machine]
system = 'emscripten'
cpu_family = 'wasm32'
cpu = 'wasm32'
endian = 'little'
```

Pass this file with `--cross-file wasm.txt` when configuring the project.

If building C++ with `node-addon-api`, it must be installed and available with a `require('node-addon-api')`.

If building to WASM, `emnapi` must be installed and available with a `require('emnapi')` and `C` must be enabled as language.

If building to WASM with async support, multi-threading must be explicitly enabled:
```python
thread_dep = dependency('threads')
addon = napi.extension_module(
  'example_addon',
  [ 'src/example_main.cc' ],
  dependencies: [ thread_dep ],
  install: true
  )
```
In this case the resulting WASM will require [`COOP`/`COEP`](https://web.dev/articles/coop-coep) when loaded in a browser.

Node.js always has async support and including the `thread` dependency is a no-op when building to native.

## Advanced options

The module supports a number of Node-API specific options (these are the default values):

```python
addon = napi.extension_module(
  'example_addon',
  [ 'src/example_main.cc' ],
  node_api_options: {
    'async_pool':       4,
    'es6':              true,
    'stack':            '2MB',
    'swig':             false,
    'environments':     [ 'node', 'web', 'webview', 'worker' ]
  })
```

* `async_pool`: (*applies only to WASM*) sets the maximum number of simultaneously running async operations, must not exceed the `c_thread_count` / `cpp_thread_count` `meson` options which set the number of `emscripten` worker threads
* `es6`: (*applies only to WASM*) determines if `emscripten` will produce a CJS or ES6 WASM loader
* `stack`: (*applies only to WASM*) the maximum stack size, WASM cannot grow its stack
* `swig`: disables a number of warnings on the four major supported compilers (`gcc`, `clang`, `MSVC` and `emscripten`) triggered by the generated C++ code by SWIG
* `environments`: (*applies only to WASM*) determines the list of supported environments by the `emscripten` WASM loader, in particular, omitting `node` will produce a loader that does not work in Node.js, but can be bundled cleanly and without any extra configuration with most bundlers such as `webpack`
