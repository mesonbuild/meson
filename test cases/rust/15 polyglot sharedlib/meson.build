project('adder', 'c', 'rust', version: '1.0.0')

if build_machine.system() != 'linux'
    error('MESON_SKIP_TEST, this test only works on Linux. Patches welcome.')
endif

thread_dep = dependency('threads')
dl_dep = meson.get_compiler('c').find_library('dl', required: false)
m_dep = meson.get_compiler('c').find_library('m', required: false)

rl = static_library('radder', 'adder.rs', rust_crate_type: 'staticlib')

l = shared_library('adder', 'adder.c',
    c_args: '-DBUILDING_ADDER',
    link_with: rl,
    version: '1.0.0',
    soversion: '1',
    link_args: '-Wl,-u,adder_add', # Ensure that Rust code is not removed as unused.
    dependencies: [thread_dep, dl_dep, m_dep])
test('adder', executable('addertest', 'addertest.c', link_with: l))
