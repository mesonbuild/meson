# Copyright © 2017 Dylan Baker
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

project('149 install_link test', 'c')

if host_machine.system() == 'windows'
  error('MESON_SKIP_TEST this test is not relavent on windows')
endif

foo = executable(
  'foo',
  'foo.c',
  install : true,
)

install_link(foo, 'bar', install_dir : get_option('bindir'))
install_link(foo, 'ish', install_dir : get_option('bindir'), type : 'hard')
install_link(foo, 'bar2', install_dir : join_paths(get_option('bindir'), 'subdir'))
install_link(foo, 'ish2', install_dir : join_paths(get_option('bindir'), 'subdir'), type : 'hard')


# Test an executable with a custom install_dir
custom_exe = executable(
  'custom',
  'foo.c',
  install : true,
  install_dir : 'custom',
)
install_link(custom_exe, 'custom2', install_dir : get_option('bindir'), type : 'hard')
install_link(custom_exe, 'custom3', install_dir : get_option('bindir'))

# Test a library
libfoo = static_library(
  'foo',
  'foo.c',
  install : true,
)
install_link(libfoo, 'libbar', install_dir : get_option('libdir'), type : 'hard')
install_link(libfoo, 'libish', install_dir : get_option('libdir'))

# Test a hard link with non-installed target
# 
# This is only legal when using hard links, because of the nature of hard
# links.
libone = shared_library(
  'one',
  'foo.c',
  install : false,
)
install_link(libone, 'libtwo', install_dir : get_option('libdir'), type : 'hard')

subdir('1/2/3')
