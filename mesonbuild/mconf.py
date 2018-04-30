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
import sys
import argparse
import shlex
from . import (coredata, mesonlib, build)

def buildparser():
    parser = argparse.ArgumentParser(prog='meson configure')
    coredata.register_builtin_arguments(parser)

    parser.add_argument('directory', nargs='*')
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
                choices_col.append('[{0}]'.format(', '.join(make_lower_case(opt['choices']))))
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

    def set_options(self, options):
        for o in options:
            if '=' not in o:
                raise ConfException('Value "%s" not of type "a=b".' % o)
            (k, v) = o.split('=', 1)
            if coredata.is_builtin_option(k):
                self.coredata.set_builtin_option(k, v)
            elif k in self.coredata.backend_options:
                tgt = self.coredata.backend_options[k]
                tgt.set_value(v)
            elif k in self.coredata.user_options:
                tgt = self.coredata.user_options[k]
                tgt.set_value(v)
            elif k in self.coredata.compiler_options:
                tgt = self.coredata.compiler_options[k]
                tgt.set_value(v)
            elif k in self.coredata.base_options:
                tgt = self.coredata.base_options[k]
                tgt.set_value(v)
            elif k.endswith('_link_args'):
                lang = k[:-10]
                if lang not in self.coredata.external_link_args:
                    raise ConfException('Unknown language %s in linkargs.' % lang)
                # TODO, currently split on spaces, make it so that user
                # can pass in an array string.
                newvalue = shlex.split(v)
                self.coredata.external_link_args[lang] = newvalue
            elif k.endswith('_args'):
                lang = k[:-5]
                if lang not in self.coredata.external_args:
                    raise ConfException('Unknown language %s in compile args' % lang)
                # TODO same fix as above
                newvalue = shlex.split(v)
                self.coredata.external_args[lang] = newvalue
            else:
                raise ConfException('Unknown option %s.' % k)

    def print_conf(self):
        print('Core properties:')
        print('  Source dir', self.build.environment.source_dir)
        print('  Build dir ', self.build.environment.build_dir)
        print('\nCore options:\n')
        carr = []
        for key in ['buildtype', 'warning_level', 'werror', 'strip', 'unity', 'default_library', 'install_umask']:
            carr.append({'name': key,
                         'descr': coredata.get_builtin_option_description(key),
                         'value': self.coredata.get_builtin_option(key),
                         'choices': coredata.get_builtin_option_choices(key)})
        self.print_aligned(carr)
        if not self.coredata.backend_options:
            print('  No backend options\n')
        else:
            bearr = []
            for k in sorted(self.coredata.backend_options):
                o = self.coredata.backend_options[k]
                bearr.append({'name': k, 'descr': o.description, 'value': o.value, 'choices': ''})
            self.print_aligned(bearr)
        print('\nBase options:')
        if not self.coredata.base_options:
            print('  No base options\n')
        else:
            coarr = []
            for k in sorted(self.coredata.base_options):
                o = self.coredata.base_options[k]
                coarr.append({'name': k, 'descr': o.description, 'value': o.value, 'choices': o.choices})
            self.print_aligned(coarr)
        print('\nCompiler arguments:')
        for (lang, args) in self.coredata.external_args.items():
            print('  ' + lang + '_args', str(args))
        print('\nLinker args:')
        for (lang, args) in self.coredata.external_link_args.items():
            print('  ' + lang + '_link_args', str(args))
        print('\nCompiler options:')
        if not self.coredata.compiler_options:
            print('  No compiler options\n')
        else:
            coarr = []
            for k in self.coredata.compiler_options:
                o = self.coredata.compiler_options[k]
                coarr.append({'name': k, 'descr': o.description, 'value': o.value, 'choices': ''})
            self.print_aligned(coarr)
        print('\nDirectories:')
        parr = []
        for key in ['prefix',
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
                    'sharedstatedir',
                    ]:
            parr.append({'name': key,
                         'descr': coredata.get_builtin_option_description(key),
                         'value': self.coredata.get_builtin_option(key),
                         'choices': coredata.get_builtin_option_choices(key)})
        self.print_aligned(parr)
        print('\nProject options:')
        if not self.coredata.user_options:
            print('  This project does not have any options')
        else:
            optarr = []
            for key in sorted(self.coredata.user_options):
                opt = self.coredata.user_options[key]
                if (opt.choices is None) or (not opt.choices):
                    # Zero length list or string
                    choices = ''
                else:
                    choices = opt.choices
                optarr.append({'name': key,
                               'descr': opt.description,
                               'value': opt.value,
                               'choices': choices})
            self.print_aligned(optarr)
        print('\nTesting options:')
        tarr = []
        for key in ['stdsplit', 'errorlogs']:
            tarr.append({'name': key,
                         'descr': coredata.get_builtin_option_description(key),
                         'value': self.coredata.get_builtin_option(key),
                         'choices': coredata.get_builtin_option_choices(key)})
        self.print_aligned(tarr)


def run(args):
    args = mesonlib.expand_arguments(args)
    if not args:
        args = [os.getcwd()]
    options = buildparser().parse_args(args)
    coredata.filter_builtin_options(options, args)
    if len(options.directory) > 1:
        print('%s <build directory>' % args[0])
        print('If you omit the build directory, the current directory is substituted.')
        return 1
    if not options.directory:
        builddir = os.getcwd()
    else:
        builddir = options.directory[0]
    try:
        c = Conf(builddir)
        save = False
        if len(options.projectoptions) > 0:
            c.set_options(options.projectoptions)
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


if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
