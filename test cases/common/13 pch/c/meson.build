cc = meson.get_compiler('c')
cc_id = cc.get_id()
if cc_id == 'lcc'
  error('MESON_SKIP_TEST: Elbrus compiler does not support PCH.')
endif

exe = executable('prog', 'prog.c',
c_pch : ['pch/prog_pch.c', 'pch/prog.h'])
