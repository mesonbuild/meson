project('internal dependencies', 'c', 'rust')

test_prog = find_program('test.py')

static = static_library('static', 'lib.c', c_args : '-DMODE="static"')
exe = executable('static', 'main.rs', link_with : static)
test('static linkage', test_prog, args : [exe, 'This is a static C library'])

# Shared linkage with rust doesn't work on macOS with meson, yet
if host_machine.system() != 'darwin'
  shared = shared_library('shared', 'lib.c', c_args : '-DMODE="shared"')
  exe = executable('shared', 'main.rs', link_with : shared)
  test('shared linkage', test_prog, args : [exe, 'This is a shared C library'])
endif
