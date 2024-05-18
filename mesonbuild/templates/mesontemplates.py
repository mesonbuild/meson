# SPDX-License-Identifier: Apache-2.0
# Copyright 2019 The Meson development team

from __future__ import annotations

import typing as T

if T.TYPE_CHECKING:
    from ..minit import Arguments

# Template for generating Meson build file for an executable
meson_executable_template = '''
project('{project_name}', {language},
  version: '{version}',
  default_options: [{default_options}])

executable('{executable}',
           {sourcespec},
           {depspec}
           install: true)
'''

# Template for generating Meson build file for a Java executable (JAR)
meson_jar_template = '''
project('{project_name}', 'java',
  version: '{version}',
  default_options: [{default_options}])

jar('{executable}',
    {sourcespec},
    {depspec}
    main_class: '{main_class}',
    install: true)
'''


def create_meson_build(options: Arguments) -> None:
    # Check if the project type is an executable
    if options.type != 'executable':
        raise SystemExit('\nGenerating a meson.build file from existing sources is\n'
                         'supported only for project type "executable".\n'
                         'Run meson init in an empty directory to create a sample project.')

    # Set default options based on the programming language
    default_options = ['warning_level=3']
    if options.language == 'cpp':
        # Set the C++ standard for C++ projects
        default_options += ['cpp_std=c++14']

    # Format default options as a string
    formatted_default_options = ', '.join(f"'{x}'" for x in default_options)

    # Format source files specification
    sourcespec = ',\n           '.join(f"'{x}'" for x in options.srcfiles)

    # Format dependency specification
    depspec = ''
    if options.deps:
        depspec = '\n           dependencies: [\n              '
        depspec += ',\n              '.join(f"dependency('{x}')"
                                             for x in options.deps.split(','))
        depspec += '],'

    # Determine the language of the project
    language = f"'{options.language}'"
    if options.language == 'java':
        # For Java projects, the language should be set to 'java' and additional parameters are required
        language = "'java'"

    # Determine the appropriate template based on the project language
    template = meson_executable_template
    if options.language == 'java':
        template = meson_jar_template

    # Generate the content for the meson.build file
    content = template.format(project_name=options.name,
                               language=language,
                               version=options.version,
                               executable=options.executable,
                               sourcespec=sourcespec,
                               depspec=depspec,
                               default_options=formatted_default_options)

    # Write the content to the meson.build file
    with open('meson.build', 'w', encoding='utf-8') as file:
        file.write(content)

    # Print the generated meson.build file content
    print('Generated meson.build file:\n\n' + content)
