project('cppmodules gcc', 'cpp', default_options: ['cpp_std=c++20'])

cxx = meson.get_compiler('cpp')
# The argument which enables modules is -fmodules-ts in GCC 14 and -fmodules in GCC 15
modules_args = cxx.version().version_compare('>=15') ? ['-fmodules'] : ['-fmodules-ts']

e = executable(
    'modtest',
    'main.cpp',
    'src0.cxx',
    'src1.cxx',
    cpp_args: modules_args,
)

test('modtest', e)
