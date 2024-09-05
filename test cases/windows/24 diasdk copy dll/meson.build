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
dia_dll_name = dia.get_variable('dll')
fs = import('fs')
fs.copyfile( dia_dll_name )

conf = configuration_data()
conf.set('msdia_dll_name', fs.name(dia_dll_name))
configure_file(input: 'config.h.in', output: 'config.h', configuration: conf)

executable('dia_from_dll', ['dia_from_dll.cpp'], dependencies: [dia])
