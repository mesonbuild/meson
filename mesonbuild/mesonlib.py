# Copyright 2012-2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A library of random helper functionality."""

import stat
import time
import platform, subprocess, operator, os, shutil, re
import collections

from glob import glob

class MesonException(Exception):
    '''Exceptions thrown by Meson'''

class EnvironmentException(MesonException):
    '''Exceptions thrown while processing and creating the build environment'''

class FileMode:
    # The first triad is for owner permissions, the second for group permissions,
    # and the third for others (everyone else).
    # For the 1st character:
    #  'r' means can read
    #  '-' means not allowed
    # For the 2nd character:
    #  'w' means can write
    #  '-' means not allowed
    # For the 3rd character:
    #  'x' means can execute
    #  's' means can execute and setuid/setgid is set (owner/group triads only)
    #  'S' means cannot execute and setuid/setgid is set (owner/group triads only)
    #  't' means can execute and sticky bit is set ("others" triads only)
    #  'T' means cannot execute and sticky bit is set ("others" triads only)
    #  '-' means none of these are allowed
    #
    # The meanings of 'rwx' perms is not obvious for directories; see:
    # https://www.hackinglinuxexposed.com/articles/20030424.html
    #
    # For information on this notation such as setuid/setgid/sticky bits, see:
    # https://en.wikipedia.org/wiki/File_system_permissions#Symbolic_notation
    symbolic_perms_regex = re.compile('[r-][w-][xsS-]' # Owner perms
                                      '[r-][w-][xsS-]' # Group perms
                                      '[r-][w-][xtT-]') # Others perms

    def __init__(self, perms=None, owner=None, group=None):
        self.perms_s = perms
        self.perms = self.perms_s_to_bits(perms)
        self.owner = owner
        self.group = group

    def __repr__(self):
        ret = '<FileMode: {!r} owner={} group={}'
        return ret.format(self.perms_s, self.owner, self.group)

    @classmethod
    def perms_s_to_bits(cls, perms_s):
        '''
        Does the opposite of stat.filemode(), converts strings of the form
        'rwxr-xr-x' to st_mode enums which can be passed to os.chmod()
        '''
        if perms_s is None:
            # No perms specified, we will not touch the permissions
            return -1
        eg = 'rwxr-xr-x'
        if not isinstance(perms_s, str):
            msg = 'Install perms must be a string. For example, {!r}'
            raise MesonException(msg.format(eg))
        if len(perms_s) != 9 or not cls.symbolic_perms_regex.match(perms_s):
            msg = 'File perms {!r} must be exactly 9 chars. For example, {!r}'
            raise MesonException(msg.format(perms_s, eg))
        perms = 0
        # Owner perms
        if perms_s[0] == 'r':
            perms |= stat.S_IRUSR
        if perms_s[1] == 'w':
            perms |= stat.S_IWUSR
        if perms_s[2] == 'x':
            perms |= stat.S_IXUSR
        elif perms_s[2] == 'S':
            perms |= stat.S_ISUID
        elif perms_s[2] == 's':
            perms |= stat.S_IXUSR
            perms |= stat.S_ISUID
        # Group perms
        if perms_s[3] == 'r':
            perms |= stat.S_IRGRP
        if perms_s[4] == 'w':
            perms |= stat.S_IWGRP
        if perms_s[5] == 'x':
            perms |= stat.S_IXGRP
        elif perms_s[5] == 'S':
            perms |= stat.S_ISGID
        elif perms_s[5] == 's':
            perms |= stat.S_IXGRP
            perms |= stat.S_ISGID
        # Others perms
        if perms_s[6] == 'r':
            perms |= stat.S_IROTH
        if perms_s[7] == 'w':
            perms |= stat.S_IWOTH
        if perms_s[8] == 'x':
            perms |= stat.S_IXOTH
        elif perms_s[8] == 'T':
            perms |= stat.S_ISVTX
        elif perms_s[8] == 't':
            perms |= stat.S_IXOTH
            perms |= stat.S_ISVTX
        return perms

class File:
    def __init__(self, is_built, subdir, fname):
        self.is_built = is_built
        self.subdir = subdir
        self.fname = fname
        assert(isinstance(self.subdir, str))
        assert(isinstance(self.fname, str))

    def __str__(self):
        return self.relative_name()

    def __repr__(self):
        ret = '<File: {0}'
        if not self.is_built:
            ret += ' (not built)'
        ret += '>'
        return ret.format(self.relative_name())

    @staticmethod
    def from_source_file(source_root, subdir, fname):
        if not os.path.isfile(os.path.join(source_root, subdir, fname)):
            raise MesonException('File %s does not exist.' % fname)
        return File(False, subdir, fname)

    @staticmethod
    def from_built_file(subdir, fname):
        return File(True, subdir, fname)

    @staticmethod
    def from_absolute_file(fname):
        return File(False, '', fname)

    def rel_to_builddir(self, build_to_src):
        if self.is_built:
            return self.relative_name()
        else:
            return os.path.join(build_to_src, self.subdir, self.fname)

    def absolute_path(self, srcdir, builddir):
        absdir = srcdir
        if self.is_built:
            absdir = builddir
        return os.path.join(absdir, self.relative_name())

    def endswith(self, ending):
        return self.fname.endswith(ending)

    def split(self, s):
        return self.fname.split(s)

    def __eq__(self, other):
        return (self.fname, self.subdir, self.is_built) == (other.fname, other.subdir, other.is_built)

    def __hash__(self):
        return hash((self.fname, self.subdir, self.is_built))

    def relative_name(self):
        return os.path.join(self.subdir, self.fname)

def get_meson_script(env, script):
    '''
    Given the path of `meson.py`/`meson`, get the path of a meson script such
    as `mesonintrospect` or `mesontest`.
    '''
    meson_py = env.get_build_command()
    (base, ext) = os.path.splitext(meson_py)
    return os.path.join(os.path.dirname(base), script + ext)

def get_compiler_for_source(compilers, src):
    for comp in compilers:
        if comp.can_compile(src):
            return comp
    raise RuntimeError('No specified compiler can handle file {!s}'.format(src))

def classify_unity_sources(compilers, sources):
    compsrclist = {}
    for src in sources:
        comp = get_compiler_for_source(compilers, src)
        if comp not in compsrclist:
            compsrclist[comp] = [src]
        else:
            compsrclist[comp].append(src)
    return compsrclist

def flatten(item):
    if not isinstance(item, list):
        return [item]
    result = []
    for i in item:
        if isinstance(i, list):
            result += flatten(i)
        else:
            result.append(i)
    return result

def is_osx():
    return platform.system().lower() == 'darwin'

def is_linux():
    return platform.system().lower() == 'linux'

def is_windows():
    platname = platform.system().lower()
    return platname == 'windows' or 'mingw' in platname

def is_cygwin():
    platname = platform.system().lower()
    return platname.startswith('cygwin')

def is_debianlike():
    return os.path.isfile('/etc/debian_version')

def exe_exists(arglist):
    try:
        p = subprocess.Popen(arglist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate()
        if p.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    return False

def detect_vcs(source_dir):
    vcs_systems = [
        dict(name = 'git',        cmd = 'git', repo_dir = '.git', get_rev = 'git describe --dirty=+', rev_regex = '(.*)', dep = '.git/logs/HEAD'),
        dict(name = 'mercurial',  cmd = 'hg',  repo_dir = '.hg',  get_rev = 'hg id -i',               rev_regex = '(.*)', dep = '.hg/dirstate'),
        dict(name = 'subversion', cmd = 'svn', repo_dir = '.svn', get_rev = 'svn info',               rev_regex = 'Revision: (.*)', dep = '.svn/wc.db'),
        dict(name = 'bazaar',     cmd = 'bzr', repo_dir = '.bzr', get_rev = 'bzr revno',              rev_regex = '(.*)', dep = '.bzr'),
    ]

    segs = source_dir.replace('\\', '/').split('/')
    for i in range(len(segs), -1, -1):
        curdir = '/'.join(segs[:i])
        for vcs in vcs_systems:
            if os.path.isdir(os.path.join(curdir, vcs['repo_dir'])) and shutil.which(vcs['cmd']):
                vcs['wc_dir'] = curdir
                return vcs
    return None

def grab_leading_numbers(vstr, strict=False):
    result = []
    for x in vstr.split('.'):
        try:
            result.append(int(x))
        except ValueError as e:
            if strict:
                msg = 'Invalid version to compare against: {!r}; only ' \
                      'numeric digits separated by "." are allowed: ' + str(e)
                raise MesonException(msg.format(vstr))
            break
    return result

numpart = re.compile('[0-9.]+')

def version_compare(vstr1, vstr2, strict=False):
    match = numpart.match(vstr1.strip())
    if match is None:
        msg = 'Uncomparable version string {!r}.'
        raise MesonException(msg.format(vstr1))
    vstr1 = match.group(0)
    if vstr2.startswith('>='):
        cmpop = operator.ge
        vstr2 = vstr2[2:]
    elif vstr2.startswith('<='):
        cmpop = operator.le
        vstr2 = vstr2[2:]
    elif vstr2.startswith('!='):
        cmpop = operator.ne
        vstr2 = vstr2[2:]
    elif vstr2.startswith('=='):
        cmpop = operator.eq
        vstr2 = vstr2[2:]
    elif vstr2.startswith('='):
        cmpop = operator.eq
        vstr2 = vstr2[1:]
    elif vstr2.startswith('>'):
        cmpop = operator.gt
        vstr2 = vstr2[1:]
    elif vstr2.startswith('<'):
        cmpop = operator.lt
        vstr2 = vstr2[1:]
    else:
        cmpop = operator.eq
    varr1 = grab_leading_numbers(vstr1, strict)
    varr2 = grab_leading_numbers(vstr2, strict)
    return cmpop(varr1, varr2)

def version_compare_many(vstr1, conditions):
    if not isinstance(conditions, (list, tuple, frozenset)):
        conditions = [conditions]
    found = []
    not_found = []
    for req in conditions:
        if not version_compare(vstr1, req, strict=True):
            not_found.append(req)
        else:
            found.append(req)
    return not_found == [], not_found, found

def default_libdir():
    if is_debianlike():
        try:
            pc = subprocess.Popen(['dpkg-architecture', '-qDEB_HOST_MULTIARCH'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL)
            (stdo, _) = pc.communicate()
            if pc.returncode == 0:
                archpath = stdo.decode().strip()
                return 'lib/' + archpath
        except Exception:
            pass
    if os.path.isdir('/usr/lib64') and not os.path.islink('/usr/lib64'):
        return 'lib64'
    return 'lib'

def default_libexecdir():
    # There is no way to auto-detect this, so it must be set at build time
    return 'libexec'

def default_prefix():
    return 'c:/' if is_windows() else '/usr/local'

def get_library_dirs():
    if is_windows():
        return ['C:/mingw/lib'] # Fixme
    if is_osx():
        return ['/usr/lib'] # Fix me as well.
    # The following is probably Debian/Ubuntu specific.
    # /usr/local/lib is first because it contains stuff
    # installed by the sysadmin and is probably more up-to-date
    # than /usr/lib. If you feel that this search order is
    # problematic, please raise the issue on the mailing list.
    unixdirs = ['/usr/local/lib', '/usr/lib', '/lib']
    plat = subprocess.check_output(['uname', '-m']).decode().strip()
    # This is a terrible hack. I admit it and I'm really sorry.
    # I just don't know what the correct solution is.
    if plat == 'i686':
        plat = 'i386'
    if plat.startswith('arm'):
        plat = 'arm'
    unixdirs += glob('/usr/lib/' + plat + '*')
    if os.path.exists('/usr/lib64'):
        unixdirs.append('/usr/lib64')
    unixdirs += glob('/lib/' + plat + '*')
    if os.path.exists('/lib64'):
        unixdirs.append('/lib64')
    unixdirs += glob('/lib/' + plat + '*')
    return unixdirs


def do_replacement(regex, line, confdata):
    match = re.search(regex, line)
    while match:
        varname = match.group(1)
        if varname in confdata:
            (var, desc) = confdata.get(varname)
            if isinstance(var, str):
                pass
            elif isinstance(var, int):
                var = str(var)
            else:
                raise RuntimeError('Tried to replace a variable with something other than a string or int.')
        else:
            var = ''
        line = line.replace('@' + varname + '@', var)
        match = re.search(regex, line)
    return line

def do_mesondefine(line, confdata):
    arr = line.split()
    if len(arr) != 2:
        raise MesonException('#mesondefine does not contain exactly two tokens: %s', line.strip())
    varname = arr[1]
    try:
        (v, desc) = confdata.get(varname)
    except KeyError:
        return '/* #undef %s */\n' % varname
    if isinstance(v, bool):
        if v:
            return '#define %s\n' % varname
        else:
            return '#undef %s\n' % varname
    elif isinstance(v, int):
        return '#define %s %d\n' % (varname, v)
    elif isinstance(v, str):
        return '#define %s %s\n' % (varname, v)
    else:
        raise MesonException('#mesondefine argument "%s" is of unknown type.' % varname)


def do_conf_file(src, dst, confdata):
    try:
        with open(src, encoding='utf-8') as f:
            data = f.readlines()
    except Exception as e:
        raise MesonException('Could not read input file %s: %s' % (src, str(e)))
    # Only allow (a-z, A-Z, 0-9, _, -) as valid characters for a define
    # Also allow escaping '@' with '\@'
    regex = re.compile(r'[^\\]?@([-a-zA-Z0-9_]+)@')
    result = []
    for line in data:
        if line.startswith('#mesondefine'):
            line = do_mesondefine(line, confdata)
        else:
            line = do_replacement(regex, line, confdata)
        result.append(line)
    dst_tmp = dst + '~'
    with open(dst_tmp, 'w', encoding='utf-8') as f:
        f.writelines(result)
    shutil.copymode(src, dst_tmp)
    replace_if_different(dst, dst_tmp)

def dump_conf_header(ofilename, cdata):
    with open(ofilename, 'w', encoding='utf-8') as ofile:
        ofile.write('''/*
 * Autogenerated by the Meson build system.
 * Do not edit, your changes will be lost.
 */

#pragma once

''')
        for k in sorted(cdata.keys()):
            (v, desc) = cdata.get(k)
            if desc:
                ofile.write('/* %s */\n' % desc)
            if isinstance(v, bool):
                if v:
                    ofile.write('#define %s\n\n' % k)
                else:
                    ofile.write('#undef %s\n\n' % k)
            elif isinstance(v, (int, str)):
                ofile.write('#define %s %s\n\n' % (k, v))
            else:
                raise MesonException('Unknown data type in configuration file entry: ' + k)

def replace_if_different(dst, dst_tmp):
    # If contents are identical, don't touch the file to prevent
    # unnecessary rebuilds.
    different = True
    try:
        with open(dst, 'r') as f1, open(dst_tmp, 'r') as f2:
            if f1.read() == f2.read():
                different = False
    except FileNotFoundError:
        pass
    if different:
        os.replace(dst_tmp, dst)
    else:
        os.unlink(dst_tmp)

def typeslistify(item, types):
    '''
    Ensure that type(@item) is one of @types or a
    list of items all of which are of type @types
    '''
    if isinstance(item, types):
        item = [item]
    if not isinstance(item, list):
        raise MesonException('Item must be a list or one of {!r}'.format(types))
    for i in item:
        if i is not None and not isinstance(i, types):
            raise MesonException('List item must be one of {!r}'.format(types))
    return item

def stringlistify(item):
    return typeslistify(item, str)

def expand_arguments(args):
    expended_args = []
    for arg in args:
        if not arg.startswith('@'):
            expended_args.append(arg)
            continue

        args_file = arg[1:]
        try:
            with open(args_file) as f:
                extended_args = f.read().split()
            expended_args += extended_args
        except Exception as e:
            print('Error expanding command line arguments, %s not found' % args_file)
            print(e)
            return None
    return expended_args

def Popen_safe(args, write=None, stderr=subprocess.PIPE, **kwargs):
    p = subprocess.Popen(args, universal_newlines=True,
                         close_fds=False,
                         stdout=subprocess.PIPE,
                         stderr=stderr, **kwargs)
    o, e = p.communicate(write)
    return p, o, e

def commonpath(paths):
    '''
    For use on Python 3.4 where os.path.commonpath is not available.
    We currently use it everywhere so this receives enough testing.
    '''
    # XXX: Replace me with os.path.commonpath when we start requiring Python 3.5
    import pathlib
    if not paths:
        raise ValueError('arg is an empty sequence')
    common = pathlib.PurePath(paths[0])
    for path in paths[1:]:
        new = []
        path = pathlib.PurePath(path)
        for c, p in zip(common.parts, path.parts):
            if c != p:
                break
            new.append(c)
        # Don't convert '' into '.'
        if not new:
            common = ''
            break
        new = os.path.join(*new)
        common = pathlib.PurePath(new)
    return str(common)

def iter_regexin_iter(regexiter, initer):
    '''
    Takes each regular expression in @regexiter and tries to search for it in
    every item in @initer. If there is a match, returns that match.
    Else returns False.
    '''
    for regex in regexiter:
        for ii in initer:
            if not isinstance(ii, str):
                continue
            match = re.search(regex, ii)
            if match:
                return match.group()
    return False

def _substitute_values_check_errors(command, values):
    # Error checking
    inregex = ('@INPUT([0-9]+)?@', '@PLAINNAME@', '@BASENAME@')
    outregex = ('@OUTPUT([0-9]+)?@', '@OUTDIR@')
    if '@INPUT@' not in values:
        # Error out if any input-derived templates are present in the command
        match = iter_regexin_iter(inregex, command)
        if match:
            m = 'Command cannot have {!r}, since no input files were specified'
            raise MesonException(m.format(match))
    else:
        if len(values['@INPUT@']) > 1:
            # Error out if @PLAINNAME@ or @BASENAME@ is present in the command
            match = iter_regexin_iter(inregex[1:], command)
            if match:
                raise MesonException('Command cannot have {!r} when there is '
                                     'more than one input file'.format(match))
        # Error out if an invalid @INPUTnn@ template was specified
        for each in command:
            if not isinstance(each, str):
                continue
            match = re.search(inregex[0], each)
            if match and match.group() not in values:
                m = 'Command cannot have {!r} since there are only {!r} inputs'
                raise MesonException(m.format(match.group(), len(values['@INPUT@'])))
    if '@OUTPUT@' not in values:
        # Error out if any output-derived templates are present in the command
        match = iter_regexin_iter(outregex, command)
        if match:
            m = 'Command cannot have {!r} since there are no outputs'
            raise MesonException(m.format(match))
    else:
        # Error out if an invalid @OUTPUTnn@ template was specified
        for each in command:
            if not isinstance(each, str):
                continue
            match = re.search(outregex[0], each)
            if match and match.group() not in values:
                m = 'Command cannot have {!r} since there are only {!r} outputs'
                raise MesonException(m.format(match.group(), len(values['@OUTPUT@'])))

def substitute_values(command, values):
    '''
    Substitute the template strings in the @values dict into the list of
    strings @command and return a new list. For a full list of the templates,
    see get_filenames_templates_dict()

    If multiple inputs/outputs are given in the @values dictionary, we
    substitute @INPUT@ and @OUTPUT@ only if they are the entire string, not
    just a part of it, and in that case we substitute *all* of them.
    '''
    # Error checking
    _substitute_values_check_errors(command, values)
    # Substitution
    outcmd = []
    for vv in command:
        if not isinstance(vv, str):
            outcmd.append(vv)
        elif '@INPUT@' in vv:
            inputs = values['@INPUT@']
            if vv == '@INPUT@':
                outcmd += inputs
            elif len(inputs) == 1:
                outcmd.append(vv.replace('@INPUT@', inputs[0]))
            else:
                raise MesonException("Command has '@INPUT@' as part of a "
                                     "string and more than one input file")
        elif '@OUTPUT@' in vv:
            outputs = values['@OUTPUT@']
            if vv == '@OUTPUT@':
                outcmd += outputs
            elif len(outputs) == 1:
                outcmd.append(vv.replace('@OUTPUT@', outputs[0]))
            else:
                raise MesonException("Command has '@OUTPUT@' as part of a "
                                     "string and more than one output file")
        # Append values that are exactly a template string.
        # This is faster than a string replace.
        elif vv in values:
            outcmd.append(values[vv])
        # Substitute everything else with replacement
        else:
            for key, value in values.items():
                if key in ('@INPUT@', '@OUTPUT@'):
                    # Already done above
                    continue
                vv = vv.replace(key, value)
            outcmd.append(vv)
    return outcmd

def get_filenames_templates_dict(inputs, outputs):
    '''
    Create a dictionary with template strings as keys and values as values for
    the following templates:

    @INPUT@  - the full path to one or more input files, from @inputs
    @OUTPUT@ - the full path to one or more output files, from @outputs
    @OUTDIR@ - the full path to the directory containing the output files

    If there is only one input file, the following keys are also created:

    @PLAINNAME@ - the filename of the input file
    @BASENAME@ - the filename of the input file with the extension removed

    If there is more than one input file, the following keys are also created:

    @INPUT0@, @INPUT1@, ... one for each input file

    If there is more than one output file, the following keys are also created:

    @OUTPUT0@, @OUTPUT1@, ... one for each output file
    '''
    values = {}
    # Gather values derived from the input
    if inputs:
        # We want to substitute all the inputs.
        values['@INPUT@'] = inputs
        for (ii, vv) in enumerate(inputs):
            # Write out @INPUT0@, @INPUT1@, ...
            values['@INPUT{}@'.format(ii)] = vv
        if len(inputs) == 1:
            # Just one value, substitute @PLAINNAME@ and @BASENAME@
            values['@PLAINNAME@'] = plain = os.path.split(inputs[0])[1]
            values['@BASENAME@'] = os.path.splitext(plain)[0]
    if outputs:
        # Gather values derived from the outputs, similar to above.
        values['@OUTPUT@'] = outputs
        for (ii, vv) in enumerate(outputs):
            values['@OUTPUT{}@'.format(ii)] = vv
        # Outdir should be the same for all outputs
        values['@OUTDIR@'] = os.path.split(outputs[0])[0]
        # Many external programs fail on empty arguments.
        if values['@OUTDIR@'] == '':
            values['@OUTDIR@'] = '.'
    return values


def windows_proof_rmtree(f):
    # On Windows if anyone is holding a file open you can't
    # delete it. As an example an anti virus scanner might
    # be scanning files you are trying to delete. The only
    # way to fix this is to try again and again.
    delays = [0.1, 0.1, 0.2, 0.2, 0.2, 0.5, 0.5, 1, 1, 1, 1, 2]
    for d in delays:
        try:
            shutil.rmtree(f)
            return
        except (OSError, PermissionError):
            time.sleep(d)
    # Try one last time and throw if it fails.
    shutil.rmtree(f)

class OrderedSet(collections.MutableSet):
    """A set that preserves the order in which items are added, by first
    insertion.
    """
    def __init__(self, iterable=None):
        self.__container = collections.OrderedDict()
        if iterable:
            self.update(iterable)

    def __contains__(self, value):
        return value in self.__container

    def __iter__(self):
        return iter(self.__container.keys())

    def __len__(self):
        return len(self.__container)

    def __repr__(self):
        # Don't print 'OrderedSet("")' for an empty set.
        if self.__container:
            return 'OrderedSet("{}")'.format(
                '", "'.join(repr(e) for e in self.__container.keys()))
        return 'OrderedSet()'

    def add(self, value):
        self.__container[value] = None

    def discard(self, value):
        if value in self.__container:
            del self.__container[value]

    def update(self, iterable):
        for item in iterable:
            self.__container[item] = None

    def difference(self, set_):
        return type(self)(e for e in self if e not in set_)
