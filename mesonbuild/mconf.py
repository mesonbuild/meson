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
import argparse
from . import (coredata, mesonlib, build)

def buildparser():
    parser = argparse.ArgumentParser(prog='meson configure')
    coredata.register_builtin_arguments(parser)

    parser.add_argument('builddir', nargs='?', default='.')
    parser.add_argument('--clearcache', action='store_true', default=False,
                        help='Clear cached state (e.g. found dependencies)')
    return parser


class ConfException(mesonlib.MesonException):
    pass


class Conf:
    def __init__(self, build_dir):
        self.build_dir = build_dir
        if not os.path.isdir(os.path.join(build_dir, 'meson-private')):
            raise ConfException('Directory %s does not seem to be a Meson build directory.' % build_dir)
        self.build = build.load(self.build_dir)
        self.coredata = coredata.load(self.build_dir)

    def clear_cache(self):
        self.coredata.deps = {}

    def set_options(self, options):
        self.coredata.set_options(options)

    def save(self):
        # Only called if something has changed so overwrite unconditionally.
        coredata.save(self.coredata, self.build_dir)
        # We don't write the build file because any changes to it
        # are erased when Meson is executed the next time, i.e. when
        # Ninja is run.

    @staticmethod
    def print_aligned(arr):
        def make_lower_case(val):
            if isinstance(val, bool):
                return str(val).lower()
            elif isinstance(val, list):
                return [make_lower_case(i) for i in val]
            else:
                return str(val)

        if not arr:
            return

        titles = {'name': 'Option', 'descr': 'Description', 'value': 'Current Value', 'choices': 'Possible Values'}

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
                    choices_col.append('[{0}]'.format(', '.join(make_lower_case(opt['choices']))))
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
        for k in sorted(options):
            o = options[k]
            d = o.description
            v = o.value
            c = o.choices
            if isinstance(o, coredata.UserUmaskOption):
                v = format(v, '04o')
            arr.append({'name': k, 'descr': d, 'value': v, 'choices': c})
        self.print_aligned(arr)

    def print_conf(self):
        print('Core properties:')
        print('  Source dir', self.build.environment.source_dir)
        print('  Build dir ', self.build.environment.build_dir)

        dir_option_names = ['prefix',
                            'libdir',
                            'libexecdir',
                            'bindir',
                            'sbindir',
                            'includedir',
                            'datadir',
                            'mandir',
                            'infodir',
                            'localedir',
                            'sysconfdir',
                            'localstatedir',
                            'sharedstatedir']
        test_option_names = ['stdsplit',
                             'errorlogs']
        core_option_names = [k for k in self.coredata.builtins if k not in dir_option_names + test_option_names]

        dir_options = {k: o for k, o in self.coredata.builtins.items() if k in dir_option_names}
        test_options = {k: o for k, o in self.coredata.builtins.items() if k in test_option_names}
        core_options = {k: o for k, o in self.coredata.builtins.items() if k in core_option_names}

        self.print_options('Core options', core_options)
        self.print_options('Backend options', self.coredata.backend_options)
        self.print_options('Base options', self.coredata.base_options)
        self.print_options('Compiler options', self.coredata.compiler_options)
        self.print_options('Directories', dir_options)
        self.print_options('Project options', self.coredata.user_options)
        self.print_options('Testing options', test_options)


def run(args):
    args = mesonlib.expand_arguments(args)
    options = buildparser().parse_args(args)
    coredata.parse_cmd_line_options(options)
    builddir = os.path.abspath(os.path.realpath(options.builddir))
    try:
        c = Conf(builddir)
        save = False
        if len(options.cmd_line_options) > 0:
            c.set_options(options.cmd_line_options)
            save = True
        elif options.clearcache:
            c.clear_cache()
            save = True
        else:
            c.print_conf()
        if save:
            c.save()
    except ConfException as e:
        print('Meson configurator encountered an error:')
        raise e
    return 0
