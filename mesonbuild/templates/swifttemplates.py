# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from mesonbuild.templates.sampleimpl import SampleImpl
import re


hello_swift_template = '''

let PROJECT_NAME = "{project_name}"

func main() {{
    print("This is project \\(PROJECT_NAME).\\n")
}}

main()
'''

hello_swift_meson_template = '''project('{project_name}', 'swift',
    version : '{version}',
    default_options: ['warning_level=3'])

exe = executable('{exe_name}', '{source_name}',
  install : true)

test('basic', exe)
'''

lib_swift_template = '''
/* This function will not be exported and is not
 * directly callable by users of this library.
 */
private func internal_function() -> Int {{
    return 0
}}

public func {function_name}() -> Int {{
    return internal_function()
}}
'''

lib_swift_test_template = '''import {lib_name}


func main() {{
    print("Result: \\({function_name}())\\n")
}}

main()
'''

lib_swift_meson_template = '''project('{project_name}', 'swift',
  version : '{version}',
  default_options : ['warning_level=3'])

stlib = static_library('{lib_name}', '{source_file}',
  install : true,
  gnu_symbol_visibility : 'hidden'
)

test_exe = executable('{test_exe_name}', '{test_source_file}',
  link_with : stlib)
test('{test_name}', test_exe)

# Make this library usable as a Meson subproject.
{ltoken}_dep = declare_dependency(
  include_directories: include_directories('.'),
  link_with : stlib)
'''


class SwiftProject(SampleImpl):
    def __init__(self, options):
        super().__init__()
        self.name = options.name
        self.version = options.version

    def create_executable(self):
        lowercase_token = re.sub(r'[^a-z0-9]', '_', self.name.lower())
        source_name = lowercase_token + '.swift'
        open(source_name, 'w').write(hello_swift_template.format(project_name=self.name))
        open('meson.build', 'w').write(hello_swift_meson_template.format(project_name=self.name,
                                                                         exe_name=lowercase_token,
                                                                         source_name=source_name,
                                                                         version=self.version))

    def create_library(self):
        lowercase_token = re.sub(r'[^a-z0-9]', '_', self.name.lower())
        uppercase_token = lowercase_token.upper()
        function_name = lowercase_token[0:3] + '_func'
        test_exe_name = lowercase_token + '_test'
        lib_swift_name = lowercase_token + '.swift'
        test_swift_name = lowercase_token + '_test.swift'
        kwargs = {'utoken': uppercase_token,
                  'ltoken': lowercase_token,
                  'header_dir': lowercase_token,
                  'function_name': function_name,
                  'source_file': lib_swift_name,
                  'test_source_file': test_swift_name,
                  'test_exe_name': test_exe_name,
                  'project_name': self.name,
                  'lib_name': lowercase_token,
                  'test_name': lowercase_token,
                  'version': self.version,
                  }
        open(lib_swift_name, 'w').write(lib_swift_template.format(**kwargs))
        open(test_swift_name, 'w').write(lib_swift_test_template.format(**kwargs))
        open('meson.build', 'w').write(lib_swift_meson_template.format(**kwargs))
