project(
  'Hello World for meson',
  ['c', 'cpp']
)

napi = import('node-api')

run_command(['npm', '--prefix', meson.global_source_root(), 'install'], check: true)

addon = napi.extension_module(
  'hello_world',
  [ 'hello_world.cc' ],
  install: true
  )

assert(get_option('enabled'))
assert(not get_option('disabled'))
assert(not get_option('default_false'))
assert(get_option('default_true'))
assert(get_option('string') == 'string')
assert(get_option('choice') == 'a')
assert(get_option('lib').enabled())
assert(get_option('array')[0] == 'a')
assert(get_option('array')[1] == 'b')
assert(get_option('array')[2] == 'c')

summary({
  'enabled': get_option('enabled'),
  'disabled': get_option('disabled'),
  'true': get_option('default_true'),
  'false': get_option('default_false'),
  'string': get_option('string'),
  'choice': get_option('choice'),
  'lib': get_option('lib'),
  'array': get_option('array'),
})

if host_machine.system() == 'emscripten'
  napi.test('hello_world_test', 'test-wasm.mjs', addon)
else
  napi.test('hello_world_test', 'test-native.cjs', addon)
endif
