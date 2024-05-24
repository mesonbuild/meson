napi = import('node-api')

addon = napi.extension_module(
  'hello_subworld',
  [ 'hello_subworld.cc' ],
  install: true,
  install_dir: 'sub'
  )

if host_machine.system() == 'emscripten'
  napi.test('hello_world_test', 'test-wasm.mjs', addon)
else
  napi.test('hello_world_test', 'test-native.cjs', addon)
endif
