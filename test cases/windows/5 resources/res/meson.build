win = import('windows')

configure_file(input: 'dummy.h', output: 'dummy-gen.h', copy: true)

res = win.compile_resources('myres.rc',
  depend_files: 'sample.ico',
  include_directories : inc,
  implicit_include_directories : true,
  args : [['-DFOO'], '-DBAR'])

# test that with MSVC tools, LIB/LINK invokes CVTRES with correct /MACHINE
static_library('reslib', res, 'dummy.c')
shared_library('shreslib', res, 'dummy.c')
