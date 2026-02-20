project('basic-convert',
        ['c', 'cpp', 'rust'],
        license : 'MIT',
        meson_version : '>= 1.4.0',
        default_options : [
          'buildtype=debugoptimized',
          'b_ndebug=if-release',
          'c_std=c11',
          'cpp_std=c++17',
          'rust_std=2021',
          'build.rust_std=2021',
        ],
)

cc = meson.get_compiler('c')
cpp = meson.get_compiler('cpp')

cc.check_header('pthread_np.h')
cc.has_header_symbol('errno.h', 'program_invocation_name')
cc.has_function('qsort_s')
cc.has_function_attribute('optimize')

code_bsd = '''#include <stdlib.h>
void cb(void *a, const void *b, const void *c) {}
int main(void) { qsort_r(0, 0, 0, 0, cb); return 0; }
'''
cpp.links(code_bsd, name: 'BSD qsort_r')


inc = include_directories('include')

commonlib = static_library('commonlib', 'common.c', include_directories: inc)

shared_library('simplelib', 'main.c',
  include_directories: inc,
  link_with: commonlib
)

subdir('subdir2')
subdir('subdir1')
subdir('subdir3')
subdir('subdir4')
subdir('subdir5')
