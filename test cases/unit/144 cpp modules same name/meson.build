project('cppmodules same name', 'cpp', default_options: ['cpp_std=c++20'])

cxx = meson.get_compiler('cpp')
if cxx.get_id() == 'msvc'
    modules_args = ['/interface']
elif cxx.version().version_compare('>=15')
    # The argument which enables modules is -fmodules-ts in GCC 14 and -fmodules in GCC 15
    modules_args = ['-fmodules']
else
    modules_args = ['-fmodules-ts']
endif

# Two targets provide a module with the same name, each one has its own compiled module.
liba = static_library('a', 'ma.cxx', cpp_args: modules_args)
libb = static_library('b', 'mb.cxx', cpp_args: modules_args)

a = executable('app_a', 'a.cpp', link_with: liba, cpp_args: modules_args)
b = executable('app_b', 'b.cpp', link_with: libb, cpp_args: modules_args)

test('a', a)
test('b', b)
