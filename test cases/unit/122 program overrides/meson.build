project('program overrides')

fs = import('fs')

if build_machine.system() == 'windows'
  prog = 'cmd'
else
  prog = 'sh'
endif

native_prog = find_program(prog, native: true)
cross_prog = find_program(prog, native: false)

if get_option('machine') == 'build'
  assert(fs.name(native_prog.full_path()) == 'prog.sh', 'override did not occur')
  assert(fs.name(cross_prog.full_path()) == prog, 'override did not occur')
else
  assert(fs.name(cross_prog.full_path()) == 'prog.sh', 'override did not occur')
  assert(fs.name(native_prog.full_path()) == prog, 'override did not occur')
endif
