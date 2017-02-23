project('run target', 'c')

# deprecated format, fix once we remove support for it.
run_target('mycommand','scripts/script.sh')

# Make it possible to run built programs.
# In cross builds exe_wrapper should be added if it exists.

exe = executable('helloprinter', 'helloprinter.c')
run_target('runhello',
  command : [exe, 'argument'])

converter = find_program('converter.py')

hex = custom_target('exe.hex',
  input : exe,
  output : 'exe.hex',
  command : [converter, '@INPUT@', '@OUTPUT@',
  ],
)

fakeburner = find_program('fakeburner.py')

# These emulates the Arduino flasher application. It sandwiches the filename inside
# a packed argument. Thus we need to declare it manually.
run_target('upload',
  command : [fakeburner, 'x:@0@:y'.format(exe.full_path())],
  depends : exe,
)

run_target('upload2',
  command : [fakeburner, 'x:@0@:y'.format(hex.full_path())],
  depends : hex,
)

python3 = find_program('python3', required : false)
if not python3.found()
  python3 = find_program('python')
endif

run_target('py3hi',
  command : [python3, '-c', 'print("I am Python3.")'])

run_target('check_exists',
  command : [find_program('check_exists.py'), files('helloprinter.c')])

# What if the output of a custom_target is the command to
# execute. Obviously this will not work as hex is not an
# executable but test that the output is generated correctly.
run_target('donotrunme',
  command : hex)
