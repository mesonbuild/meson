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

import sys, os
import pickle
import argparse
from . import coredata, mesonlib

parser = argparse.ArgumentParser()

parser.add_argument('-D', action='append', default=[], dest='sets',
                    help='Set an option to the given value.')
parser.add_argument('directory', nargs='*')
parser.add_argument('--clearcache', action='store_true', default=False,
                    help='Clear cached state (e.g. found dependencies)')

class ConfException(mesonlib.MesonException):
    pass

class Conf:
    def __init__(self, build_dir):
        self.build_dir = build_dir
        self.coredata_file = os.path.join(build_dir, 'meson-private/coredata.dat')
        self.build_file = os.path.join(build_dir, 'meson-private/build.dat')
        if not os.path.isfile(self.coredata_file) or not os.path.isfile(self.build_file):
            raise ConfException('Directory %s does not seem to be a Meson build directory.' % build_dir)
        with open(self.coredata_file, 'rb') as f:
            self.coredata = pickle.load(f)
        with open(self.build_file, 'rb') as f:
            self.build = pickle.load(f)
        if self.coredata.version != coredata.version:
            raise ConfException('Version mismatch (%s vs %s)' %
                                (coredata.version, self.coredata.version))

    def clear_cache(self):
        self.coredata.deps = {}

    def save(self):
        # Only called if something has changed so overwrite unconditionally.
        with open(self.coredata_file, 'wb') as f:
            pickle.dump(self.coredata, f)
        # We don't write the build file because any changes to it
        # are erased when Meson is executed the next time, i.e. whne
        # Ninja is run.

    def print_aligned(self, arr):
        if not arr:
            return
        titles = {'name': 'Option', 'descr': 'Description', 'value': 'Current Value', 'choices': 'Possible Values'}
        len_name = longest_name = len(titles['name'])
        len_descr = longest_descr = len(titles['descr'])
        len_value = longest_value = len(titles['value'])
        longest_choices = 0 # not printed if we don't get any optional values

        # calculate the max length of each
        for x in arr:
            name = x['name']
            descr = x['descr']
            value = x['value'] if isinstance(x['value'], str) else str(x['value']).lower()
            choices = ''
            if isinstance(x['choices'], list):
                if x['choices']:
                    x['choices'] = [s if isinstance(s, str) else str(s).lower() for s in x['choices']]
                    choices = '[%s]' % ', '.join(map(str, x['choices']))
            elif x['choices']:
                choices = x['choices'] if isinstance(x['choices'], str) else str(x['choices']).lower()

            longest_name = max(longest_name, len(name))
            longest_descr = max(longest_descr, len(descr))
            longest_value = max(longest_value, len(value))
            longest_choices = max(longest_choices, len(choices))

            # update possible non strings
            x['value'] = value
            x['choices'] = choices

        # prints header
        namepad = ' ' * (longest_name - len_name)
        valuepad = ' ' * (longest_value - len_value)
        if longest_choices:
            len_choices = len(titles['choices'])
            longest_choices = max(longest_choices, len_choices)
            choicepad = ' ' * (longest_choices - len_choices)
            print('  %s%s %s%s %s%s %s' % (titles['name'], namepad, titles['value'], valuepad, titles['choices'], choicepad, titles['descr']))
            print('  %s%s %s%s %s%s %s' % ('-' * len_name, namepad, '-' * len_value, valuepad, '-' * len_choices, choicepad, '-' * len_descr))
        else:
            print('  %s%s %s%s %s' % (titles['name'], namepad, titles['value'], valuepad, titles['descr']))
            print('  %s%s %s%s %s' % ('-' * len_name, namepad, '-' * len_value, valuepad, '-' * len_descr))

        # print values
        for i in arr:
            name = i['name']
            descr = i['descr']
            value = i['value']
            choices = i['choices']

            namepad = ' ' * (longest_name - len(name))
            valuepad = ' ' * (longest_value - len(value))
            if longest_choices:
                choicespad = ' ' * (longest_choices - len(choices))
                f = '  %s%s %s%s %s%s %s' % (name, namepad, value, valuepad, choices, choicespad, descr)
            else:
                f = '  %s%s %s%s %s' % (name, namepad, value, valuepad, descr)

            print(f)

    def set_options(self, options):
        for o in options:
            if '=' not in o:
                raise ConfException('Value "%s" not of type "a=b".' % o)
            (k, v) = o.split('=', 1)
            if coredata.is_builtin_option(k):
                self.coredata.set_builtin_option(k, v)
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
                newvalue = v.split()
                self.coredata.external_link_args[lang] = newvalue
            elif k.endswith('_args'):
                lang = k[:-5]
                if lang not in self.coredata.external_args:
                    raise ConfException('Unknown language %s in compile args' % lang)
                # TODO same fix as above
                newvalue = v.split()
                self.coredata.external_args[lang] = newvalue
            else:
                raise ConfException('Unknown option %s.' % k)

    def print_conf(self):
        print('Core properties:')
        print('  Source dir', self.build.environment.source_dir)
        print('  Build dir ', self.build.environment.build_dir)
        print('')
        print('Core options:')
        carr = []
        for key in ['buildtype', 'warning_level', 'werror', 'strip', 'unity', 'default_library']:
            carr.append({'name': key,
                         'descr': coredata.get_builtin_option_description(key),
                         'value': self.coredata.get_builtin_option(key),
                         'choices': coredata.get_builtin_option_choices(key)})
        self.print_aligned(carr)
        print('')
        print('Base options:')
        okeys = sorted(self.coredata.base_options.keys())
        if not okeys:
            print('  No base options\n')
        else:
            coarr = []
            for k in okeys:
                o = self.coredata.base_options[k]
                coarr.append({'name': k, 'descr': o.description, 'value': o.value, 'choices': ''})
            self.print_aligned(coarr)
        print('')
        print('Compiler arguments:')
        for (lang, args) in self.coredata.external_args.items():
            print('  ' + lang + '_args', str(args))
        print('')
        print('Linker args:')
        for (lang, args) in self.coredata.external_link_args.items():
            print('  ' + lang + '_link_args', str(args))
        print('')
        print('Compiler options:')
        okeys = sorted(self.coredata.compiler_options.keys())
        if not okeys:
            print('  No compiler options\n')
        else:
            coarr = []
            for k in okeys:
                o = self.coredata.compiler_options[k]
                coarr.append({'name': k, 'descr': o.description, 'value': o.value, 'choices': ''})
            self.print_aligned(coarr)
        print('')
        print('Directories:')
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
        print('')
        print('Project options:')
        if not self.coredata.user_options:
            print('  This project does not have any options')
        else:
            options = self.coredata.user_options
            keys = list(options.keys())
            keys.sort()
            optarr = []
            for key in keys:
                opt = options[key]
                if (opt.choices is None) or (not opt.choices):
                    # Zero length list or string
                    choices = ''
                else:
                    # A non zero length list or string, convert to string
                    choices = str(opt.choices)
                optarr.append({'name': key,
                               'descr': opt.description,
                               'value': opt.value,
                               'choices': choices})
            self.print_aligned(optarr)
        print('')
        print('Testing options:')
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
    options = parser.parse_args(args)
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
        if len(options.sets) > 0:
            c.set_options(options.sets)
            save = True
        elif options.clearcache:
            c.clear_cache()
            save = True
        else:
            c.print_conf()
        if save:
            c.save()
    except ConfException as e:
        print('Meson configurator encountered an error:\n')
        print(e)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
