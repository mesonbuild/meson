#!/usr/bin/env python3

# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import urllib.request, json
import sys, os
import configparser
import shutil
try:
    import ssl
    has_ssl = True
    API_ROOT = 'https://wrapdb.mesonbuild.com/v1/'
except ImportError:
    print('Warning: ssl not available, traffic not authenticated.')
    has_ssl = False
    API_ROOT = 'http://wrapdb.mesonbuild.com/v1/'

from glob import glob

wrapdb_certificate = '''-----BEGIN CERTIFICATE-----
MIIFkzCCA3ugAwIBAgIJAIjVMWLmbJWUMA0GCSqGSIb3DQEBCwUAMGAxCzAJBgNV
BAYTAkZJMRUwEwYDVQQHDAxEZWZhdWx0IENpdHkxGjAYBgNVBAoMEVRoZSBNZXNv
biBQcm9qZWN0MR4wHAYDVQQDDBV3cmFwZGIubWVzb25idWlsZC5jb20wHhcNMTUw
NzIxMTk0NjI1WhcNMTYwNzIwMTk0NjI1WjBgMQswCQYDVQQGEwJGSTEVMBMGA1UE
BwwMRGVmYXVsdCBDaXR5MRowGAYDVQQKDBFUaGUgTWVzb24gUHJvamVjdDEeMBwG
A1UEAwwVd3JhcGRiLm1lc29uYnVpbGQuY29tMIICIjANBgkqhkiG9w0BAQEFAAOC
Ag8AMIICCgKCAgEArucsF2GNXW6PqGlW3egD3LxIX+YTWc7MscM5MFryoQEdCsxm
ME50J2bKZxyJIO+0bCyjvGQNbQxNIvu03ftMYVvbr949km+qafFy63U+QISXOdK1
oAPIeQnxjwTt+xK/2E8NjChQeWMOb6iX0hsxRtBWoL35SP541xGjgjWKOJTErqcV
YdDiiTaChZMb9oV4qNEipBKHvU0EmLsF1Lm8psw332QlR5eqmCk12LtV7l5kVH38
XD+aDpuB5CajcWdEQMDk4rDW6HkjNGnxYRWglMop1WbQvBLVlQ3r16BQT/Gz6x/B
5CLNjiQ1D9LzaGK0UUr2NnxXiZyE0DgNVK9HlNilE4tjapY4mRK2XanGKuCVIGhY
xuKB2UI2XbKXweNphHZh5L6a5tutxqkcj+ic0J7Fk+Kyk5smmjQC6DNRxEiQ88CJ
v7K29KaoqN0q/Gp5abc0YOXR9uA2L8TFbd+I58flSPL9XB/iYcTB4ExIHvYhzSjZ
P0HvkA3mpFpWcvpbGAhA4JkPBQL8jgUQlZnbKb2EdXKEwR7ccOuEEpQW0WL+qGBV
vm2xyrO+0Xr1pz0NKiPiBTi6pT883/9Jq1ybngBlyx1xBAF0cxJI8OrdkvYR0U2D
8I94AwKJRGiYgwsR/0OEY1CBXZDEs29AJYy8S+W1VUphwwL0+7meqUue1ucCAwEA
AaNQME4wHQYDVR0OBBYEFBHwvUp78l9J1g1LmElHnh3clzyBMB8GA1UdIwQYMBaA
FBHwvUp78l9J1g1LmElHnh3clzyBMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEL
BQADggIBAGiS/N3rchOTNADL9iGPEwTBt4aN3RzGALoxmQz/xahyr4NwsjY8rag5
hVr1M6eZ3+NTRRC3fgPMGYVBbuN51N9SffEgRjAZzOkmBX7fLwTFY3ywsddWiomF
8kstor3103IEzPej9nNlQOht7+HKd1ggchji8+zFFGedmOxLweY5985Ze6TNaqVD
ONZ2u7RmkfpgNUDoMsfHyRnENcsQrJXXS1Pp2TRhb/+0NrqrdSorIKYlt5FP/GkZ
OBdm61RfwHLi72SmkeDGPeOYoS2b0SYNuoXHIX+fjVOOIES0A4jRXsQC10cKGZws
IuXNVLrWaLQq874op0oVteR5guW7Rr0KGRNA6MJt67H2VxPtoyaxCXjygoX0+a92
KlDBb8geKOkNfoXg4fRF2Qxh+j5VLBgJyR+x/YYUdG89kDc+Tb3By3PVWi5ypAPC
UPYkc0F8hB9h9KYe78UnzqIRw+YjFN8bKJQS+DXBLyRmp35gn1yp/Vw2O7Vk+E7m
SuYF28YTKF/woZWdJH1aQDO0erUBXdiycZVeKbdm3jenNPHTiF/Wt22CXIlGjj83
G+eGrvfQVk3oXRn+YlypIbxkV8eI1wOina799oiflQmvV8EevAS4dkJObahV6rtZ
qf3ZjWGS595JCwW0fq6AAtL+ygMSr6+DcjGibYbWTL3GmiMtUeWr
-----END CERTIFICATE-----
'''

help_templ = '''This program allows you to manage your Wrap dependencies
using the online wrap database http://wrapdb.mesonbuild.com.

Run this command in your top level source directory.

Usage:

%s <command> [options]

Commands:

 list - show all available projects
 search - search the db by name
 install - install the specified project
 update - update the project to its newest available release
 info - show available versions of a project
 status - show installed and available versions of your projects

'''


def print_help():
    print(help_templ % sys.argv[0])

def build_ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.options |= ssl.OP_NO_SSLv2
    ctx.options |= ssl.OP_NO_SSLv3
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(cadata=wrapdb_certificate)
    return ctx

def get_result(urlstring):
    if has_ssl:
        u = urllib.request.urlopen(urlstring, context=build_ssl_context())
    else:
        u = urllib.request.urlopen(urlstring)
    data = u.read().decode('utf-8')
    jd = json.loads(data)
    if jd['output'] != 'ok':
        print('Got bad output from server.')
        print(data)
        sys.exit(1)
    return jd

def get_projectlist():
    jd = get_result(API_ROOT + 'projects')
    projects = jd['projects']
    return projects

def list_projects():
    projects = get_projectlist()
    for p in projects:
        print(p)

def search(name):
    jd = get_result(API_ROOT + 'query/byname/' + name)
    for p in jd['projects']:
        print(p)

def get_latest_version(name):
    jd = get_result(API_ROOT + 'query/get_latest/' + name)
    branch = jd['branch']
    revision = jd['revision']
    return (branch, revision)

def install(name):
    if not os.path.isdir('subprojects'):
        print('Subprojects dir not found. Run this script in your source root directory.')
        sys.exit(1)
    if os.path.isdir(os.path.join('subprojects', name)):
        print('Subproject directory for this project already exists.')
        sys.exit(1)
    wrapfile = os.path.join('subprojects', name + '.wrap')
    if os.path.exists(wrapfile):
        print('Wrap file already exists.')
        sys.exit(1)
    (branch, revision) = get_latest_version(name)
    u = urllib.request.urlopen(API_ROOT + 'projects/%s/%s/%s/get_wrap' % (name, branch, revision))
    data = u.read()
    open(wrapfile, 'wb').write(data)
    print('Installed', name, 'branch', branch, 'revision', revision)

def get_current_version(wrapfile):
    cp = configparser.ConfigParser()
    cp.read(wrapfile)
    cp = cp['wrap-file']
    patch_url = cp['patch_url']
    arr = patch_url.split('/')
    branch = arr[-3]
    revision = int(arr[-2])
    return (branch, revision, cp['directory'], cp['source_filename'], cp['patch_filename'])

def update(name):
    if not os.path.isdir('subprojects'):
        print('Subprojects dir not found. Run this command in your source root directory.')
        sys.exit(1)
    wrapfile = os.path.join('subprojects', name + '.wrap')
    if not os.path.exists(wrapfile):
        print('Project', name, 'is not in use.')
        sys.exit(1)
    (branch, revision, subdir, src_file, patch_file) = get_current_version(wrapfile)
    (new_branch, new_revision) = get_latest_version(name)
    if new_branch == branch and new_revision == revision:
        print('Project', name, 'is already up to date.')
        sys.exit(0)
    u = urllib.request.urlopen(API_ROOT + 'projects/%s/%s/%d/get_wrap' % (name, new_branch, new_revision))
    data = u.read()
    shutil.rmtree(os.path.join('subprojects', subdir), ignore_errors=True)
    try:
        os.unlink(os.path.join('subprojects/packagecache', src_file))
    except FileNotFoundError:
        pass
    try:
        os.unlink(os.path.join('subprojects/packagecache', patch_file))
    except FileNotFoundError:
        pass
    open(wrapfile, 'wb').write(data)
    print('Updated', name, 'to branch', new_branch, 'revision', new_revision)

def info(name):
    jd = get_result(API_ROOT + 'projects/' + name)
    versions = jd['versions']
    if len(versions) == 0:
        print('No available versions of', name)
        sys.exit(0)
    print('Available versions of %s:' % name)
    for v in versions:
        print(' ', v['branch'], v['revision'])

def status():
    print('Subproject status')
    for w in glob('subprojects/*.wrap'):
        name = os.path.split(w)[1][:-5]
        try:
            (latest_branch, latest_revision) = get_latest_version(name)
        except Exception:
            print('', name, 'not available in wrapdb.')
            continue
        try:
            (current_branch, current_revision, _, _, _) = get_current_version(w)
        except Exception:
            print('Wrap file not from wrapdb.')
            continue
        if current_branch == latest_branch and current_revision == latest_revision:
            print('', name, 'up to date. Branch %s, revision %d.' % (current_branch, current_revision))
        else:
            print('', name, 'not up to date. Have %s %d, but %s %d is available.' % (current_branch, current_revision, latest_branch, latest_revision))

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
        print_help()
        sys.exit(0)
    command = sys.argv[1]
    args = sys.argv[2:]
    if command == 'list':
        list_projects()
    elif command == 'search':
        if len(args) != 1:
            print('Search requires exactly one argument.')
            sys.exit(1)
        search(args[0])
    elif command == 'install':
        if len(args) != 1:
            print('Install requires exactly one argument.')
            sys.exit(1)
        install(args[0])
    elif command == 'update':
        if len(args) != 1:
            print('update requires exactly one argument.')
            sys.exit(1)
        update(args[0])
    elif command == 'info':
        if len(args) != 1:
            print('info requires exactly one argument.')
            sys.exit(1)
        info(args[0])
    elif command == 'status':
        status()
    else:
        print('Unknown command', command)
        sys.exit(1)

