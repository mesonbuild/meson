project(
  'Hello World for meson',
  ['c', 'cpp']
)

napi = import('node-api')

run_command(['npm', '--prefix', meson.global_source_root(), 'install'], check: true)

addon = napi.extension_module(
  'hello_world',
  [ 'hello_world.cc' ],
  install: true,
  node_api_options: { 'environments': ['node']}
  )

if host_machine.system() == 'emscripten'
  napi.test('hello_world_test', 'test-wasm.mjs', addon)
else
  napi.test('hello_world_test', 'test-native.cjs', addon)
endif
