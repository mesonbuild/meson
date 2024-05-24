project(
  'SWIG JSE Node-API async example',
  ['c', 'cpp']
)

napi = import('node-api')

run_command(['npm', '--prefix', meson.global_source_root(), 'install'], check: true)


thread_dep = dependency('threads')
addon = napi.extension_module(
  'async_example',
  [ 'example_wrap.cxx', 'example.cxx' ],
  dependencies: [ thread_dep ],
  install: true,
  node_api_options: { 'swig': true }
  )

if host_machine.system() == 'emscripten'
  napi.test('hello_world_test', 'test-wasm.mjs', addon)
else
  napi.test('hello_world_test', 'test-native.cjs', addon)
endif
