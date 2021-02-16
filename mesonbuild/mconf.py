# Copyright 2014-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from . import coredata, environment, mesonlib, build, mintro, mlog
from .ast import AstIDGenerator
import typing as T

from .mesonlib import MachineChoice, OptionKey

if T.TYPE_CHECKING:
    import argparse
    from .coredata import UserOption

def add_arguments(parser: 'argparse.ArgumentParser') -> None:
    coredata.register_builtin_arguments(parser)
    parser.add_argument('builddir', nargs='?', default='.')
    parser.add_argument('--clearcache', action='store_true', default=False,
                        help='Clear cached state (e.g. found dependencies)')

def make_lower_case(val: T.Any) -> T.Union[str, T.List[T.Any]]:  # T.Any because of recursion...
    if isinstance(val, bool):
        return str(val).lower()
    elif isinstance(val, list):
        return [make_lower_case(i) for i in val]
    else:
        return str(val)


class ConfException(mesonlib.MesonException):
    pass


class Conf:
    def __init__(self, build_dir):
        self.build_dir = os.path.abspath(os.path.realpath(build_dir))
        if 'meson.build' in [os.path.basename(self.build_dir), self.build_dir]:
            self.build_dir = os.path.dirname(self.build_dir)
        self.build = None
        self.max_choices_line_length = 60
        self.name_col = []
        self.value_col = []
        self.choices_col = []
        self.descr_col = []
        self.has_choices = False
        self.all_subprojects: T.Set[str] = set()
        self.yielding_options: T.Set[OptionKey] = set()

        if os.path.isdir(os.path.join(self.build_dir, 'meson-private')):
            self.build = build.load(self.build_dir)
            self.source_dir = self.build.environment.get_source_dir()
            self.coredata = coredata.load(self.build_dir)
            self.default_values_only = False
        elif os.path.isfile(os.path.join(self.build_dir, environment.build_filename)):
            # Make sure that log entries in other parts of meson don't interfere with the JSON output
            mlog.disable()
            self.source_dir = os.path.abspath(os.path.realpath(self.build_dir))
            intr = mintro.IntrospectionInterpreter(self.source_dir, '', 'ninja', visitors = [AstIDGenerator()])
            intr.analyze()
            # Re-enable logging just in case
            mlog.enable()
            self.coredata = intr.coredata
            self.default_values_only = True
        else:
            raise ConfException('Directory {} is neither a Meson build directory nor a project source directory.'.format(build_dir))

    def clear_cache(self):
        self.coredata.deps.host.clear()
        self.coredata.deps.build.clear()

    def set_options(self, options):
        self.coredata.set_options(options)

    def save(self):
        # Do nothing when using introspection
        if self.default_values_only:
            return
        # Only called if something has changed so overwrite unconditionally.
        coredata.save(self.coredata, self.build_dir)
        # We don't write the build file because any changes to it
        # are erased when Meson is executed the next time, i.e. when
        # Ninja is run.

    def print_aligned(self):
        col_widths = (max([len(i) for i in self.name_col], default=0),
                      max([len(i) for i in self.value_col], default=0),
                      max([len(i) for i in self.choices_col], default=0))

        for line in zip(self.name_col, self.value_col, self.choices_col, self.descr_col):
            if self.has_choices:
                print('{0:{width[0]}} {1:{width[1]}} {2:{width[2]}} {3}'.format(*line, width=col_widths))
            else:
                print('{0:{width[0]}} {1:{width[1]}} {3}'.format(*line, width=col_widths))

    def split_options_per_subproject(self, options: 'coredata.KeyedOptionDictType') -> T.Dict[str, T.Dict[str, 'UserOption']]:
        result: T.Dict[str, T.Dict[str, 'UserOption']] = {}
        for k, o in options.items():
            subproject = k.subproject
            if k.subproject:
                k = k.as_root()
                if o.yielding and k in options:
                    self.yielding_options.add(k)
                self.all_subprojects.add(subproject)
            result.setdefault(subproject, {})[str(k)] = o
        return result

    def _add_line(self, name: OptionKey, value, choices, descr) -> None:
        self.name_col.append(' ' * self.print_margin + str(name))
        self.value_col.append(value)
        self.choices_col.append(choices)
        self.descr_col.append(descr)

    def add_option(self, name, descr, value, choices):
        if isinstance(value, list):
            value = '[{0}]'.format(', '.join(make_lower_case(value)))
        else:
            value = make_lower_case(value)

        if choices:
            self.has_choices = True
            if isinstance(choices, list):
                choices_list = make_lower_case(choices)
                current = '['
                while choices_list:
                    i = choices_list.pop(0)
                    if len(current) + len(i) >= self.max_choices_line_length:
                        self._add_line(name, value, current + ',', descr)
                        name = ''
                        value = ''
                        descr = ''
                        current = ' '
                    if len(current) > 1:
                        current += ', '
                    current += i
                choices = current + ']'
            else:
                choices = make_lower_case(choices)
        else:
            choices = ''

        self._add_line(name, value, choices, descr)

    def add_title(self, title):
        titles = {'descr': 'Description', 'value': 'Current Value', 'choices': 'Possible Values'}
        if self.default_values_only:
            titles['value'] = 'Default Value'
        self._add_line('', '', '', '')
        self._add_line(title, titles['value'], titles['choices'], titles['descr'])
        self._add_line('-' * len(title), '-' * len(titles['value']), '-' * len(titles['choices']), '-' * len(titles['descr']))

    def add_section(self, section):
        self.print_margin = 0
        self._add_line('', '', '', '')
        self._add_line(section + ':', '', '', '')
        self.print_margin = 2

    def print_options(self, title: str, options: 'coredata.KeyedOptionDictType') -> None:
        if not options:
            return
        if title:
            self.add_title(title)
        for k, o in sorted(options.items()):
            printable_value = o.printable_value()
            if k in self.yielding_options:
                printable_value = '<inherited from main project>'
            self.add_option(k, o.description, printable_value, o.choices)

    def print_conf(self):
        def print_default_values_warning():
            mlog.warning('The source directory instead of the build directory was specified.')
            mlog.warning('Only the default values for the project are printed, and all command line parameters are ignored.')

        if self.default_values_only:
            print_default_values_warning()
            print('')

        print('Core properties:')
        print('  Source dir', self.source_dir)
        if not self.default_values_only:
            print('  Build dir ', self.build_dir)

        dir_option_names = set(coredata.BUILTIN_DIR_OPTIONS)
        test_option_names = {OptionKey('errorlogs'),
                            OptionKey('stdsplit')}

        dir_options: 'coredata.KeyedOptionDictType' = {}
        test_options: 'coredata.KeyedOptionDictType' = {}
        core_options: 'coredata.KeyedOptionDictType' = {}
        for k, v in self.coredata.options.items():
            if k in dir_option_names:
                dir_options[k] = v
            elif k in test_option_names:
                test_options[k] = v
            elif k.is_builtin():
                core_options[k] = v

        host_core_options = self.split_options_per_subproject({k: v for k, v in core_options.items() if k.machine is MachineChoice.HOST})
        build_core_options = self.split_options_per_subproject({k: v for k, v in core_options.items() if k.machine is MachineChoice.BUILD})
        host_compiler_options = self.split_options_per_subproject({k: v for k, v in self.coredata.options.items() if k.is_compiler() and k.machine is MachineChoice.HOST})
        build_compiler_options = self.split_options_per_subproject({k: v for k, v in self.coredata.options.items() if k.is_compiler() and k.machine is MachineChoice.BUILD})
        project_options = self.split_options_per_subproject({k: v for k, v in self.coredata.options.items() if k.is_project()})
        show_build_options = self.default_values_only or self.build.environment.is_cross_build()

        self.add_section('Main project options')
        self.print_options('Core options', host_core_options[''])
        if show_build_options:
            self.print_options('', build_core_options[''])
        self.print_options('Backend options', {str(k): v for k, v in self.coredata.options.items() if k.is_backend()})
        self.print_options('Base options', {str(k): v for k, v in self.coredata.options.items() if k.is_base()})
        self.print_options('Compiler options', host_compiler_options.get('', {}))
        if show_build_options:
            self.print_options('', build_compiler_options.get('', {}))
        self.print_options('Directories', dir_options)
        self.print_options('Testing options', test_options)
        self.print_options('Project options', project_options.get('', {}))
        for subproject in sorted(self.all_subprojects):
            if subproject == '':
                continue
            self.add_section('Subproject ' + subproject)
            if subproject in core_options:
                self.print_options('Core options', core_options[subproject])
            if subproject in host_compiler_options:
                self.print_options('Compiler options', host_compiler_options[subproject])
            if subproject in build_compiler_options and show_build_options:
                self.print_options('', build_compiler_options[subproject])
            if subproject in project_options:
                self.print_options('Project options', project_options[subproject])
        self.print_aligned()

        # Print the warning twice so that the user shouldn't be able to miss it
        if self.default_values_only:
            print('')
            print_default_values_warning()

        self.print_nondefault_buildtype_options()

    def print_nondefault_buildtype_options(self):
        mismatching = self.coredata.get_nondefault_buildtype_args()
        if not mismatching:
            return
        print("\nThe following option(s) have a different value than the build type default\n")
        print(f'               current   default')
        for m in mismatching:
            print(f'{m[0]:21}{m[1]:10}{m[2]:10}')

def run(options):
    coredata.parse_cmd_line_options(options)
    builddir = os.path.abspath(os.path.realpath(options.builddir))
    c = None
    try:
        c = Conf(builddir)
        if c.default_values_only:
            c.print_conf()
            return 0

        save = False
        if options.cmd_line_options:
            c.set_options(options.cmd_line_options)
            coredata.update_cmd_line_file(builddir, options)
            save = True
        elif options.clearcache:
            c.clear_cache()
            save = True
        else:
            c.print_conf()
        if save:
            c.save()
            mintro.update_build_options(c.coredata, c.build.environment.info_dir)
            mintro.write_meson_info_file(c.build, [])
    except ConfException as e:
        print('Meson configurator encountered an error:')
        if c is not None and c.build is not None:
            mintro.write_meson_info_file(c.build, [e])
        raise e
    return 0
