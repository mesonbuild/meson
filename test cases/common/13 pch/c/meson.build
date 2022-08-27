cc = meson.get_compiler('c')
cc_id = cc.get_id()

if cc_id == 'lcc'
  error('MESON_SKIP_TEST: Elbrus compiler does not support PCH.')
endif

# PGI compiler only supports PCH for C++
if cc_id == 'pgi'
  subdir_done()
endif

libm = cc.find_library('m', required: false)

stlib_squared = static_library('stlib_squared', 'static_squared.c', c_pch : 'pch/static_squared_pch.h', dependencies: libm)
stlib = static_library('static', 'static.c', c_pch : 'pch/static_pch.h', dependencies: libm,
  link_whole: stlib_squared)
shlib = shared_library('shared', 'shared.c', c_pch : 'pch/shared_pch.h', dependencies: libm,
  c_args: '-DBUILDING_DLL')

exe = executable('prog', 'prog.c',
  link_with: [stlib, shlib],
  c_pch : 'pch/prog.h')
