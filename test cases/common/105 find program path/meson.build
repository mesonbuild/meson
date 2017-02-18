project('find program', 'c')

python = find_program('python3', required : false)
if not python.found()
  python = find_program('python')
endif

# Source file via string
prog = find_program('program.py')
# Source file via files()
progf = files('program.py')
# Built file
py = configure_file(input : 'program.py',
                    output : 'builtprogram.py',
                    configuration : configuration_data())

foreach f : [prog, find_program(py), find_program(progf)]
  ret = run_command(python, f.path())
  assert(ret.returncode() == 0, 'can\'t manually run @0@'.format(prog.path()))
  assert(ret.stdout().strip() == 'Found', 'wrong output from manually-run @0@'.format(prog.path()))

  ret = run_command(f)
  assert(ret.returncode() == 0, 'can\'t run @0@'.format(prog.path()))
  assert(ret.stdout().strip() == 'Found', 'wrong output from @0@'.format(prog.path()))
endforeach
