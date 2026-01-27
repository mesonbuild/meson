project('cppmodules', 'cpp', default_options: ['cpp_std=c++latest'])

cxx = meson.get_compiler('cpp')

e = executable(
    'modtest',
    'main.cpp',
    'src0.cxx',
    'src1.cxx',
    'src2.cxx',
    'src3.cxx',
    'src4.cxx',
    'src5.cxx',
    'src6.cxx',
    'src7.cxx',
    'src8.cxx',
    'src9.cxx',
    cpp_args: cxx.get_id() == 'msvc' ? ['/interface'] : ['-fmodules'],
)

test('modtest', e)
