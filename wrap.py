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

import mlog
import glob, urllib.request, os, hashlib, shutil

class PackageDefinition:
    def __init__(self, fname):
        self.values = {}
        ifile = open(fname)
        first = ifile.readline().strip()
        if first != '[mesonwrap]':
            raise RuntimeError('Invalid format of package file')
        for line in ifile:
            line = line.strip()
            if line == '':
                continue
            (k, v) = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            self.values[k] = v

    def get(self, key):
        return self.values[key]

    def has_patch(self):
        return 'patch_url' in self.values

class Resolver:
    def __init__(self, subdir_root):
        self.subdir_root = subdir_root
        self.cachedir = os.path.join(self.subdir_root, 'packagecache')

    def resolve(self, packagename):
        fname = os.path.join(self.subdir_root, packagename + '.wrap')
        if not os.path.isfile(fname):
            return None
        p = PackageDefinition(fname)
        self.download(p, packagename)
        self.extract_package(p)
        return p.get('directory')

    def get_data(self, url):
        u = urllib.request.urlopen(url)
        data = u.read()
        u.close()
        h = hashlib.sha256()
        h.update(data)
        hashvalue = h.hexdigest()
        return (data, hashvalue)

    def download(self, p, packagename):
        ofname = os.path.join(self.cachedir, p.get('source_filename'))
        if os.path.exists(ofname):
            print('Using', packagename, 'from cache.')
            return
        srcurl = p.get('source_url')
        print('Dowloading', packagename, 'from', srcurl)
        (srcdata, dhash) = self.get_data(srcurl)
        expected = p.get('source_hash')
        if dhash != expected:
            raise RuntimeError('Incorrect hash for source %s:\n %s expected\n %s actual.' % (packagename, expected, dhash))
        if p.has_patch():
            purl = p.get('patch_url')
            print('Downloading patch from', purl)
            (pdata, phash) = self.get_data(purl)
            expected = p.get('patch_hash')
            if phash != expected:
                raise RuntimeError('Incorrect hash for patch %s:\n %s expected\n %s actual.' % (packagename, expected, phash))
            open(os.path.join(self.cachedir, p.get('patch_filename')), 'wb').write(pdata)
        else:
            print('Package does not require patch.')
        open(ofname, 'wb').write(srcdata)

    def extract_package(self, package):
        if os.path.isdir(os.path.join(self.subdir_root, package.get('directory'))):
            return
        print(os.path.join(self.cachedir, package.get('source_filename')))
        shutil.unpack_archive(os.path.join(self.cachedir, package.get('source_filename')), self.subdir_root)
        if package.has_patch():
            shutil.unpack_archive(os.path.join(self.cachedir, package.get('patch_filename')), self.subdir_root)
