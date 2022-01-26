# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .boost import BoostDependency
from .cuda import CudaDependency
from .hdf5 import hdf5_factory
from .base import Dependency, InternalDependency, ExternalDependency, NotFoundDependency
from .base import (
        ExternalLibrary, DependencyException, DependencyMethods,
        BuiltinDependency, SystemDependency)
from .cmake import CMakeDependency
from .configtool import ConfigToolDependency
from .dub import DubDependency
from .framework import ExtraFrameworkDependency
from .pkgconfig import PkgConfigDependency
from .factory import DependencyFactory
from .detect import find_external_dependency, get_dep_identifier, packages, _packages_accept_language
from .dev import (
    ValgrindDependency, JNISystemDependency, JDKSystemDependency, gmock_factory, gtest_factory,
    llvm_factory, zlib_factory)
from .coarrays import coarray_factory
from .mpi import mpi_factory
from .scalapack import scalapack_factory
from .misc import (
    BlocksDependency, OpenMPDependency, cups_factory, curses_factory, gpgme_factory,
    libgcrypt_factory, libwmf_factory, netcdf_factory, pcap_factory, python3_factory,
    shaderc_factory, threads_factory, ThreadDependency, iconv_factory, intl_factory,
    dl_factory, openssl_factory, libcrypto_factory, libssl_factory,
)
from .platform import AppleFrameworks
from .qt import qt4_factory, qt5_factory, qt6_factory
from .ui import GnuStepDependency, WxDependency, gl_factory, sdl2_factory, vulkan_factory

__all__ = [
    'Dependency',
    'InternalDependency',
    'ExternalDependency',
    'SystemDependency',
    'BuiltinDependency',
    'NotFoundDependency',
    'ExternalLibrary',
    'DependencyException',
    'DependencyMethods',

    'CMakeDependency',
    'ConfigToolDependency',
    'DubDependency',
    'ExtraFrameworkDependency',
    'PkgConfigDependency',

    'DependencyFactory',

    'ThreadDependency',

    'find_external_dependency',
    'get_dep_identifier',
]

"""Dependency representations and discovery logic.

Meson attempts to largely abstract away dependency discovery information, and
to encapsulate that logic itself so that the DSL doesn't have too much direct
information. There are some cases where this is impossible/undesirable, such
as the `get_variable()` method.

Meson has four primary dependency types:
  1. pkg-config
  2. apple frameworks
  3. CMake
  4. system

Plus a few more niche ones.

When a user calls `dependency('foo')` Meson creates a list of candidates, and
tries those candidates in order to find one that matches the criteria
provided by the user (such as version requirements, or optional components
that are required.)

Except to work around bugs or handle odd corner cases, pkg-config and CMake
generally just work™, though there are exceptions. Most of this package is
concerned with dependencies that don't (always) provide CMake and/or
pkg-config files.

For these cases one needs to write a `system` dependency. These dependencies
descend directly from `ExternalDependency`, in their constructor they
manually set up the necessary link and compile args (and additional
dependencies as necessary).

For example, imagine a dependency called Foo, it uses an environment variable
called `$FOO_ROOT` to point to its install root, which looks like this:
```txt
$FOOROOT
→ include/
→ lib/
```
To use Foo, you need its include directory, and you need to link to
`lib/libfoo.ext`.

You could write code that looks like:

```python
class FooSystemDependency(ExternalDependency):

    def __init__(self, name: str, environment: 'Environment', kwargs: T.Dict[str, T.Any]):
        super().__init__(name, environment, kwargs)
        root = os.environ.get('FOO_ROOT')
        if root is None:
            mlog.debug('$FOO_ROOT is unset.')
            self.is_found = False
            return

        lib = self.clib_compiler.find_library('foo', environment, [os.path.join(root, 'lib')])
        if lib is None:
            mlog.debug('Could not find lib.')
            self.is_found = False
            return

        self.compile_args.append(f'-I{os.path.join(root, "include")}')
        self.link_args.append(lib)
        self.is_found = True
```

This code will look for `FOO_ROOT` in the environment, handle `FOO_ROOT` being
undefined gracefully, then set its `compile_args` and `link_args` gracefully.
It will also gracefully handle not finding the required lib (hopefully that
doesn't happen, but it could if, for example, the lib is only static and
shared linking is requested).

There are a couple of things about this that still aren't ideal. For one, we
don't want to be reading random environment variables at this point. Those
should actually be added to `envconfig.Properties` and read in
`environment.Environment._set_default_properties_from_env` (see how
`BOOST_ROOT` is handled). We can also handle the `static` keyword. So
now that becomes:

```python
class FooSystemDependency(ExternalDependency):

    def __init__(self, name: str, environment: 'Environment', kwargs: T.Dict[str, T.Any]):
        super().__init__(name, environment, kwargs)
        root = environment.properties[self.for_machine].foo_root
        if root is None:
            mlog.debug('foo_root is unset.')
            self.is_found = False
            return

        static = Mesonlib.LibType.STATIC if kwargs.get('static', False) else Mesonlib.LibType.SHARED
        lib = self.clib_compiler.find_library(
            'foo', environment, [os.path.join(root, 'lib')], libtype=static)
        if lib is None:
            mlog.debug('Could not find lib.')
            self.is_found = False
            return

        self.compile_args.append(f'-I{os.path.join(root, "include")}')
        self.link_args.append(lib)
        self.is_found = True
```

This is nicer in a couple of ways. First we can properly cross compile as we
are allowed to set `FOO_ROOT` for both the build and host machines, it also
means that users can override this in their machine files, and if that
environment variables changes during a Meson reconfigure Meson won't re-read
it, this is important for reproducibility. Finally, Meson will figure out
whether it should be finding `libfoo.so` or `libfoo.a` (or the platform
specific names). Things are looking pretty good now, so it can be added to
the `packages` dict below:

```python
packages.update({
    'foo': FooSystemDependency,
})
```

Now, what if foo also provides pkg-config, but it's only shipped on Unices,
or only included in very recent versions of the dependency? We can use the
`DependencyFactory` class:

```python
foo_factory = DependencyFactory(
    'foo',
    [DependencyMethods.PKGCONFIG, DependencyMethods.SYSTEM],
    system_class=FooSystemDependency,
)
```

This is a helper function that will generate a default pkg-config based
dependency, and use the `FooSystemDependency` as well. It can also handle
custom finders for pkg-config and cmake based dependencies that need some
extra help. You would then add the `foo_factory` to packages instead of
`FooSystemDependency`:

```python
packages.update({
    'foo': foo_factory,
})
```

If you have a dependency that is very complicated, (such as having multiple
implementations) you may need to write your own factory function. There are a
number of examples in this package.

_Note_ before we moved to factory functions it was common to use an
`ExternalDependency` class that would instantiate different types of
dependencies and hold the one it found. There are a number of drawbacks to
this approach, and no new dependencies should do this.
"""

# This is a dict where the keys should be strings, and the values must be one
# of:
# - An ExternalDependency subclass
# - A DependencyFactory object
# - A callable with a signature of (Environment, MachineChoice, Dict[str, Any]) -> List[Callable[[], ExternalDependency]]
packages.update({
    # From dev:
    'gtest': gtest_factory,
    'gmock': gmock_factory,
    'llvm': llvm_factory,
    'valgrind': ValgrindDependency,
    'zlib': zlib_factory,
    'jni': JNISystemDependency,
    'jdk': JDKSystemDependency,

    'boost': BoostDependency,
    'cuda': CudaDependency,

    # per-file
    'coarray': coarray_factory,
    'hdf5': hdf5_factory,
    'mpi': mpi_factory,
    'scalapack': scalapack_factory,

    # From misc:
    'blocks': BlocksDependency,
    'curses': curses_factory,
    'netcdf': netcdf_factory,
    'openmp': OpenMPDependency,
    'python3': python3_factory,
    'threads': threads_factory,
    'pcap': pcap_factory,
    'cups': cups_factory,
    'libwmf': libwmf_factory,
    'libgcrypt': libgcrypt_factory,
    'gpgme': gpgme_factory,
    'shaderc': shaderc_factory,
    'iconv': iconv_factory,
    'intl': intl_factory,
    'dl': dl_factory,
    'openssl': openssl_factory,
    'libcrypto': libcrypto_factory,
    'libssl': libssl_factory,

    # From platform:
    'appleframeworks': AppleFrameworks,

    # From ui:
    'gl': gl_factory,
    'gnustep': GnuStepDependency,
    'qt4': qt4_factory,
    'qt5': qt5_factory,
    'qt6': qt6_factory,
    'sdl2': sdl2_factory,
    'wxwidgets': WxDependency,
    'vulkan': vulkan_factory,
})
_packages_accept_language.update({
    'hdf5',
    'mpi',
    'netcdf',
    'openmp',
})
