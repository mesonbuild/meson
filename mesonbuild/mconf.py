#!/usr/bin/env python3

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

class ConfException(mesonlib.MesonException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def save(self):
        # Only called if something has changed so overwrite unconditionally.
        with open(self.coredata_file, 'wb') as f:
            pickle.dump(self.coredata, f)
        # We don't write the build file because any changes to it
        # are erased when Meson is executed the nex time, i.e. the next
        # time Ninja is run.

    def print_aligned(self, arr):
        if len(arr) == 0:
            return
        titles = ['Option', 'Description', 'Current Value', '']
        longest_name = len(titles[0])
        longest_descr = len(titles[1])
        longest_value = len(titles[2])
        longest_possible_value = len(titles[3])
        for x in arr:
            longest_name = max(longest_name, len(x[0]))
            longest_descr = max(longest_descr, len(x[1]))
            longest_value = max(longest_value, len(str(x[2])))
            if x[3]:
                longest_possible_value = max(longest_possible_value, len(x[3]))

        if longest_possible_value > 0:
            titles[3] = 'Possible Values'
        print('  %s%s %s%s %s%s %s' % (titles[0], ' '*(longest_name - len(titles[0])), titles[1], ' '*(longest_descr - len(titles[1])), titles[2], ' '*(longest_value - len(titles[2])), titles[3]))
        print('  %s%s %s%s %s%s %s' % ('-'*len(titles[0]), ' '*(longest_name - len(titles[0])), '-'*len(titles[1]), ' '*(longest_descr - len(titles[1])), '-'*len(titles[2]), ' '*(longest_value - len(titles[2])), '-'*len(titles[3])))
        for i in arr:
            name = i[0]
            descr = i[1]
            value = i[2] if isinstance(i[2], str) else str(i[2]).lower()
            possible_values = ''
            if isinstance(i[3], list):
                if len(i[3]) > 0:
                    i[3] = [s if isinstance(s, str) else str(s).lower() for s in i[3]]
                    possible_values = '[%s]' % ', '.join(map(str, i[3]))
            elif i[3]:
                possible_values = i[3] if isinstance(i[3], str) else str(i[3]).lower()
            namepad = ' '*(longest_name - len(name))
            descrpad = ' '*(longest_descr - len(descr))
            valuepad = ' '*(longest_value - len(str(value)))
            f = '  %s%s %s%s %s%s %s' % (name, namepad, descr, descrpad, value, valuepad, possible_values)
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
                if not lang in self.coredata.external_link_args:
                    raise ConfException('Unknown language %s in linkargs.' % lang)
                # TODO, currently split on spaces, make it so that user
                # can pass in an array string.
                newvalue = v.split()
                self.coredata.external_link_args[lang] = newvalue
            elif k.endswith('_args'):
                lang = k[:-5]
                if not lang in self.coredata.external_args:
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
        for key in [ 'buildtype', 'warning_level', 'werror', 'strip', 'unity', 'default_library' ]:
            carr.append([key, coredata.get_builtin_option_description(key),
                self.coredata.get_builtin_option(key), coredata.get_builtin_option_choices(key)])
        self.print_aligned(carr)
        print('')
        print('Base options:')
        okeys = sorted(self.coredata.base_options.keys())
        if len(okeys) == 0:
            print('  No base options\n')
        else:
            coarr = []
            for k in okeys:
                o = self.coredata.base_options[k]
                coarr.append([k, o.description, o.value, ''])
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
        if len(okeys) == 0:
            print('  No compiler options\n')
        else:
            coarr = []
            for k in okeys:
                o = self.coredata.compiler_options[k]
                coarr.append([k, o.description, o.value, ''])
            self.print_aligned(coarr)
        print('')
        print('Directories:')
        parr = []
        for key in [ 'prefix', 'libdir', 'libexecdir', 'bindir', 'includedir', 'datadir', 'mandir', 'localedir' ]:
            parr.append([key, coredata.get_builtin_option_description(key),
                self.coredata.get_builtin_option(key), coredata.get_builtin_option_choices(key)])
        self.print_aligned(parr)
        print('')
        print('Project options:')
        if len(self.coredata.user_options) == 0:
            print('  This project does not have any options')
        else:
            options = self.coredata.user_options
            keys = list(options.keys())
            keys.sort()
            optarr = []
            for key in keys:
                opt = options[key]
                if (opt.choices is None) or (len(opt.choices) == 0):
                    # Zero length list or string
                    choices = '';
                else:
                    # A non zero length list or string, convert to string
                    choices = str(opt.choices);
                optarr.append([key, opt.description, opt.value, choices])
            self.print_aligned(optarr)
        print('')
        print('Testing options:')
        tarr = []
        for key in [ 'stdsplit', 'errorlogs' ]:
            tarr.append([key, coredata.get_builtin_option_description(key),
                self.coredata.get_builtin_option(key), coredata.get_builtin_option_choices(key)])
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
    if len(options.directory) == 0:
        builddir = os.getcwd()
    else:
        builddir = options.directory[0]
    try:
        c = Conf(builddir)
        if len(options.sets) > 0:
            c.set_options(options.sets)
            c.save()
        else:
            c.print_conf()
    except ConfException as e:
        print('Meson configurator encountered an error:\n')
        print(e)
        return(1)
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
