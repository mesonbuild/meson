# Copyright © 2017 Intel Corporation
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

project('custom_target_index', 'c', default_options : 'c_std=c89')

py_mod = import('python3')
prog_python = py_mod.find_python()

gen = custom_target(
  'gen.[ch]',
  input : 'gen_sources.py',
  output : ['gen.c', 'gen.h'],
  command : [prog_python, '@INPUT@', '--header', '@OUTPUT1@', '--code', '@OUTPUT0@'],
)

lib = static_library(
  'libfoo',
  ['lib.c', gen[1]],
)

custom_target(
  'foo',
  input: gen[0],
  output: 'foo',
  command: [find_program('check_args.py'), '@INPUT@'],
)

subdir('subdir')
