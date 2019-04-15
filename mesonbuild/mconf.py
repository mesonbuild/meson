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

def add_arguments(parser):
    coredata.register_builtin_arguments(parser)
    parser.add_argument('builddir', nargs='?', default='.')
    parser.add_argument('--clearcache', action='store_true', default=False,
                        help='Clear cached state (e.g. found dependencies)')


def make_lower_case(val):
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
            # Reenable logging just in case
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

    def print_aligned(self, arr):
        if not arr:
            return

        titles = {'name': 'Option', 'descr': 'Description', 'value': 'Current Value', 'choices': 'Possible Values'}
        if self.default_values_only:
            titles['value'] = 'Default Value'

        name_col = [titles['name'], '-' * len(titles['name'])]
        value_col = [titles['value'], '-' * len(titles['value'])]
        choices_col = [titles['choices'], '-' * len(titles['choices'])]
        descr_col = [titles['descr'], '-' * len(titles['descr'])]

        choices_found = False
        for opt in arr:
            name_col.append(opt['name'])
            descr_col.append(opt['descr'])
            if isinstance(opt['value'], list):
                value_col.append('[{0}]'.format(', '.join(make_lower_case(opt['value']))))
            else:
                value_col.append(make_lower_case(opt['value']))
            if opt['choices']:
                choices_found = True
                if isinstance(opt['choices'], list):
                    choices_list = make_lower_case(opt['choices'])
                    current = '['
                    while choices_list:
                        i = choices_list.pop(0)
                        if len(current) + len(i) >= self.max_choices_line_length:
                            choices_col.append(current + ',')
                            name_col.append('')
                            value_col.append('')
                            descr_col.append('')
                            current = ' '
                        if len(current) > 1:
                            current += ', '
                        current += i
                    choices_col.append(current + ']')
                else:
                    choices_col.append(make_lower_case(opt['choices']))
            else:
                choices_col.append('')

        col_widths = (max([len(i) for i in name_col], default=0),
                      max([len(i) for i in value_col], default=0),
                      max([len(i) for i in choices_col], default=0),
                      max([len(i) for i in descr_col], default=0))

        for line in zip(name_col, value_col, choices_col, descr_col):
            if choices_found:
                print('  {0:{width[0]}} {1:{width[1]}} {2:{width[2]}} {3:{width[3]}}'.format(*line, width=col_widths))
            else:
                print('  {0:{width[0]}} {1:{width[1]}} {3:{width[3]}}'.format(*line, width=col_widths))

    def print_options(self, title, options):
        print('\n{}:'.format(title))
        if not options:
            print('  No {}\n'.format(title.lower()))
        arr = []
        for k, o in sorted(options.items()):
            d = o.description
            v = o.printable_value()
            c = o.choices
            arr.append({'name': k, 'descr': d, 'value': v, 'choices': c})
        self.print_aligned(arr)

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

        dir_option_names = ['bindir',
                            'datadir',
                            'includedir',
                            'infodir',
                            'libdir',
                            'libexecdir',
                            'localedir',
                            'localstatedir',
                            'mandir',
                            'prefix',
                            'sbindir',
                            'sharedstatedir',
                            'sysconfdir']
        test_option_names = ['errorlogs',
                             'stdsplit']
        core_option_names = [k for k in self.coredata.builtins if k not in dir_option_names + test_option_names]

        dir_options = {k: o for k, o in self.coredata.builtins.items() if k in dir_option_names}
        test_options = {k: o for k, o in self.coredata.builtins.items() if k in test_option_names}
        core_options = {k: o for k, o in self.coredata.builtins.items() if k in core_option_names}

        self.print_options('Core options', core_options)
        self.print_options('Core options (for host machine)', self.coredata.builtins_per_machine.host)
        self.print_options(
            'Core options (for build machine)',
            {'build.' + k: o for k, o in self.coredata.builtins_per_machine.build.items()})
        self.print_options('Backend options', self.coredata.backend_options)
        self.print_options('Base options', self.coredata.base_options)
        self.print_options('Compiler options (for host machine)', self.coredata.compiler_options.host)
        self.print_options(
            'Compiler options (for build machine)',
            {'build.' + k: o for k, o in self.coredata.compiler_options.build.items()})
        self.print_options('Directories', dir_options)
        self.print_options('Project options', self.coredata.user_options)
        self.print_options('Testing options', test_options)

        # Print the warning twice so that the user shouldn't be able to miss it
        if self.default_values_only:
            print('')
            print_default_values_warning()

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
        if len(options.cmd_line_options) > 0:
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
