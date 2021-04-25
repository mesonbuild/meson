project('.NET assembly', ['cs', 'cpp'])

cpp = meson.get_compiler('cpp')

if cpp.get_id() != 'msvc'
  error('MESON_SKIP_TEST only MSVC is supported.')
endif

dll_sources = files(
    'AssemblyInfo.cpp',
    'helper.cpp',
    'helper.h',
)

dll_lib = shared_library(
    'HelperNET',
    dll_sources,
    cpp_args: ['/clr', '/Zc:twoPhase-',],  
    override_options: ['cpp_eh=none'],
)

dll_dep = declare_dependency(
    link_with: dll_lib,
)

e = executable('prog', ['prog.cs',], dependencies: [dll_dep])
test('.NET assembly', e)

