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

# These emulates the Arduino flasher application. It sandwiches the filename inside
# a packed argument. Thus we need to declare it manually.
run_target('upload',
  command : ['fakeburner.py', 'x:@0@:y'.format(exe.full_path())],
  depends : exe,
)

run_target('upload2',
  command : ['fakeburner.py', 'x:@0@:y'.format(hex.full_path())],
  depends : hex,
)

python3 = find_program('python3')
run_target('py3hi',
  command : [python3, '-c', 'print("I am Python3.")'])
