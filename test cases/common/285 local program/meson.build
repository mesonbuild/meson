project('local program', version: '2.0')

python3 = find_program('python3')

# A module imported by prog but only available at build time.
pymod = custom_target(
  input: 'pymod.py.in',
  output: 'pymod.py',
  command: [python3, '-c', 'import shutil,sys;shutil.copy(sys.argv[1], sys.argv[2])', '@INPUT@', '@OUTPUT@'],
  build_by_default: false,
)

# Copy into builddir to have the same location as pymod.py
prog = configure_file(
  input: 'prog.py',
  output: 'prog.py',
  copy: true,
)

# Without the dependency it can't be run, but it should have the project version.
prog1 = local_program(prog)
assert(prog1.version() == '2.0')
assert(prog1.found())

prog2 = local_program(prog, depends: pymod)
assert(prog2.version() == '2.0')
assert(prog2.found())

meson.override_find_program('prog', prog2)
prog3 = find_program('prog')
assert(prog3.version() == '2.0')
assert(prog3.found())

# This should have the pymod dependency
custom_target(
  output: 'out.txt',
  command: [prog3],
  capture: true,
  build_by_default: true,
)
