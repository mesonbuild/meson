project('diatest', 'cpp')

if host_machine.system() != 'windows'
  error('MESON_SKIP_TEST: unsupported platform')
endif
cpp = meson.get_compiler('cpp', native: false)
is_msvc_clang = cpp.get_id() == 'clang' and cpp.get_define('_MSC_VER') != ''
if not ['msvc', 'clang-cl'].contains(cpp.get_id()) and not is_msvc_clang
  error('MESON_SKIP_TEST: unsupported compiler')
endif

dia = dependency('diasdk', required: true)
executable('dia_registered', ['dia_registered.cpp'], dependencies:[dia])
