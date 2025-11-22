win = import('windows')

myres = configure_file(input: 'myres.rc.in', output: 'myres.rc', copy: true)

res = win.compile_resources(myres,
  depend_files: 'sample.ico',
  include_directories : inc,
  args : [['-DFOO'], '-DBAR'])

# test that with MSVC tools, LIB/LINK invokes CVTRES with correct /MACHINE
static_library('reslib', res, 'dummy.c')
shared_library('shreslib', res, 'dummy.c')
