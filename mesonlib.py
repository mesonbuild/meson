# Copyright 2012-2014 The Meson development team

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

import platform, subprocess, operator, os, shutil
from glob import glob

def is_osx():
    return platform.system().lower() == 'darwin'

def is_linux():
    return platform.system().lower() == 'linux'

def is_windows():
    return platform.system().lower() == 'windows'

def is_debianlike():
    try:
        open('/etc/debian_version', 'r')
        return True
    except FileNotFoundError:
        return False

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
        dict(name = 'mercurial',  cmd = 'hg',  repo_dir = '.hg',  get_rev = 'hg id -n',               rev_regex = '(.*)', dep = '.hg/dirstate'),
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

def version_compare(vstr1, vstr2):
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
    varr1 = [int(x) for x in vstr1.split('.')]
    varr2 = [int(x) for x in vstr2.split('.')]
    return cmpop(varr1, varr2)

def default_libdir():
    if os.path.isfile('/etc/debian_version'):
        archpath = subprocess.check_output(['dpkg-architecture', '-qDEB_HOST_MULTIARCH']).decode().strip()
        return 'lib/' + archpath
    return 'lib'

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
