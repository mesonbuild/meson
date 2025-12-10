project('include dir test', 'c')

inc = include_directories('include')
subdir('src')

errormsg = '''Tried to form an absolute path to a dir in the source tree.
You should not do that but use relative paths instead, for
directories that are part of your project.

To get include path to any directory relative to the current dir do

incdir = include_directories(dirname)

After this incdir will contain both the current source dir as well as the
corresponding build dir. It can then be used in any subdirectory and
Meson will take care of all the busywork to make paths work.

Dirname can even be '.' to mark the current directory. Though you should
remember that the current source and build directories are always
put in the include directories by default so you only need to do
include_directories('.') if you intend to use the result in a
different subdirectory.

Note that this error message can also be triggered by
external dependencies being installed within your source
tree - it's not recommended to do this.
'''
testcase expect_error(errormsg)
  include_directories(meson.current_source_dir() / 'include')
endtestcase
# Test for issue #12217
include_directories(meson.current_source_dir() + 'xyz')

# Test to see if an include_directory object will have the subdirectory in the path
source_dir = meson.current_source_dir() / 'src'
build_dir = meson.current_build_dir() / 'src'
expected = [source_dir / '.', build_dir / '.']
# Use fs.as_posix() to ensure the results are the same across platforms.
fs = import('fs')
assert(fs.as_posix('@0@'.format(subdir_inc.to_list())) == '@0@'.format(expected))
