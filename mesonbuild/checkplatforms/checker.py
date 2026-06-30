#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import argparse
import os
import platform
import tempfile
import typing as T

from .. import environment, mesonlib, compilers
from ..envconfig import detect_cpu_family
from .defs import CompilerInfo, HostMachine, Platform


GCC_ATOMIC_BUILTINS_CODE = """
#include <stdint.h>
int main() {
    struct {
        uint64_t *v;
    } x;
    return (int)__atomic_load_n(x.v, __ATOMIC_ACQUIRE) &
           (int)__atomic_add_fetch(x.v, (uint64_t)1, __ATOMIC_ACQ_REL);
}
"""

GCC_64BIT_ATOMICS_CODE = """
#include <stdint.h>
uint64_t v;
int main() {
    return __sync_add_and_fetch(&v, (uint64_t)1);
}
"""

DIRENT_HAS_D_TYPE_PREFIX = """
#include <sys/types.h>
#include <dirent.h>
"""

XLOCALE_CODE = """
#define _GNU_SOURCE
#include <stdlib.h>
#include <locale.h>
#ifdef HAVE_XLOCALE_H
#include <xlocale.h>
#endif
int main() {
  locale_t loc = newlocale(LC_CTYPE_MASK, "C", NULL);
  const char *s = "1.0";
  char *end;
  double d = strtod_l(s, &end, loc);
  float f = strtof_l(s, &end, loc);
  freelocale(loc);
  return 0;
}
"""

GNU_QSORT_R_CODE = """
#define _GNU_SOURCE
#include <stdlib.h>

static int dcomp(const void *l, const void *r, void *t) { return 0; }

int main(int ac, char **av) {
  int arr[] = { 1 };
  void *t = NULL;
  qsort_r((void*)&arr[0], 1, 1, dcomp, t);
  return (0);
}
"""

BSD_QSORT_R_CODE = """
#include <stdlib.h>

static int dcomp(void *t, const void *l, const void *r) { return 0; }

int main(int ac, char **av) {
  int arr[] = { 1 };
  void *t = NULL;
  qsort_r((void*)&arr[0], 1, 1, t, dcomp);
  return (0);
}
"""


def run_compiler_checks(
        cross_file: str,
        name: str,
        c_flags: T.List[str],
        cpp_flags: T.List[str]) -> Platform:  # fmt: skip
    """
    This function sets up a temporary Meson environment configured with a given
    cross file to initialize C and C++ compilers.

    It then performs an extensive series of checks to probe the capabilities and
    limitations of the platform.

    The checks are mostly stolen from Mesa3D, but it could be an union of checks
    performed by important Meson enjoying projects.

    Any failures or unsupported features are recorded in a `Platform` object,
    which is returned to be serialized into a TOML configuration file.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        options = argparse.Namespace(
            cross_file=[cross_file] if cross_file else [],
            native_file=[],
            cmd_line_options={},
            builtin_keys=set(),
            d_keys=set(),
        )
        env = environment.Environment(os.getcwd(), temp_dir, options)
        cc = compilers.detect_c_compiler(env, mesonlib.MachineChoice.HOST)
        cpp = compilers.detect_cpp_compiler(env, mesonlib.MachineChoice.HOST)

        if cross_file is None:
            # Explicitly update host machine info as it might not be fully populated for native builds
            env.machines.host.cpu_family = detect_cpu_family({'c': cc, 'cpp': cpp})
            env.machines.host.cpu = platform.machine().lower()

        results = Platform(
            name=name,
            host_machine=HostMachine(
                cpu_family=env.machines.host.cpu_family,
                cpu=env.machines.host.cpu,
                system=env.machines.host.system,
                endian=env.machines.host.endian,
            ),
            c=CompilerInfo(
                compiler_id=cc.get_id(), linker_id=cc.get_linker_id(), version=cc.version
            ),
            cpp=CompilerInfo(
                compiler_id=cpp.get_id(), linker_id=cpp.get_linker_id(), version=cpp.version
            ),
            rust=CompilerInfo(compiler_id='rustc', linker_id='ld.lld', version='1.90.0'),
        )

        if cc.get_id() == 'gcc' and mesonlib.version_compare(cc.version, '< 4.4.6'):
            raise mesonlib.MesonException('When using GCC, version 4.4.6 or later is required.')

        if not cc.has_multi_link_arguments(['-Wl,--gdb-index'])[0]:
            results.c_supported_link_arguments_fails.append('-Wl,--gdb-index')

        builtins_to_detect = {
            'bswap32': 'int main() { return __builtin_bswap32(0); }',
            'bswap64': 'int main() { return __builtin_bswap64(0); }',
            'clz': '#include <strings.h>\nint main() { int x = 0; return __builtin_clz(x); }',
            'clzll': '#include <strings.h>\nint main() { long long x = 0; return __builtin_clzll(x); }',
            'ctz': '#include <strings.h>\nint main() { int x = 0; return __builtin_ctz(x); }',
            'expect': 'int main() { return __builtin_expect(0, 0); }',
            'ffs': '#include <strings.h>\nint main() { return ffs(0); }',
            'ffsll': '#include <strings.h>\nint main() { return ffsll(0); }',
            'popcount': 'int main() { return __builtin_popcount(0); }',
            'popcountll': 'int main() { return __builtin_popcountll(0); }',
            'unreachable': 'int main() { __builtin_unreachable(); }',
            'types_compatible_p': 'int main() { return __builtin_types_compatible_p(int, int); }',
        }
        for f, code in builtins_to_detect.items():
            if not cc.compiles(code, extra_args=c_flags)[0]:
                results.c_functions_fails.append(f)

        _attributes = [
            'const',
            'flatten',
            'malloc',
            'pure',
            'unused',
            'warn_unused_result',
            'weak',
            'format',
            'packed',
            'returns_nonnull',
            'alias',
            'noreturn',
        ]

        for attr in _attributes:
            if not cc.has_func_attribute(attr)[0]:
                results.c_function_attributes_fails.append(attr)

        if not cc.has_func_attribute('visibility:hidden')[0]:
            results.c_function_attributes_fails.append('visibility:hidden')

        if not cc.compiles("__uint128_t foo(void) { return 0; }", extra_args=c_flags)[0]:  # fmt: skip
            results.c_compiles_fails.append('__uint128_t')

        if not cc.links("static char unused() { return 5; } int main() { return 0; }",
                        extra_args=["-Wl,--gc-sections"])[0]:  # fmt: skip
            results.c_links_fails.append('gc-sections')

        if not cc.compiles(GCC_ATOMIC_BUILTINS_CODE, extra_args=c_flags)[0]:
            results.c_compiles_fails.append('GCC atomic builtins')

        if not cc.links(GCC_64BIT_ATOMICS_CODE, extra_args=c_flags)[0]:
            results.c_links_fails.append('GCC 64bit atomics')

        if not cc.has_header_symbol("sys/sysmacros.h", "major", "", extra_args=c_flags)[0]:  # fmt: skip
            results.c_header_symbols_fails.setdefault("sys/sysmacros.h", []).append("major")  # fmt: skip

        if not cc.has_header_symbol("sys/sysmacros.h", "minor", "", extra_args=c_flags)[0]:  # fmt: skip
            results.c_header_symbols_fails.setdefault("sys/sysmacros.h", []).append("minor")  # fmt: skip

        if not cc.has_header_symbol("sys/sysmacros.h", "makedev", "", extra_args=c_flags)[0]:  # fmt: skip
            results.c_header_symbols_fails.setdefault("sys/sysmacros.h", []).append("makedev")  # fmt: skip

        if not cc.has_header_symbol('sys/mkdev.h', 'major', '', extra_args=c_flags)[0]:
            results.c_header_symbols_fails.setdefault('sys/mkdev.h', []).append('major')

        if not cc.has_header_symbol('sys/mkdev.h', 'minor', '', extra_args=c_flags)[0]:
            results.c_header_symbols_fails.setdefault('sys/mkdev.h', []).append('minor')

        if not cc.has_header_symbol("sys/mkdev.h", "makedev", "", extra_args=c_flags)[0]:  # fmt: skip
            results.c_header_symbols_fails.setdefault("sys/mkdev.h", []).append("makedev")  # fmt: skip

        if not cc.check_header('sched.h', '', extra_args=c_flags)[0]:
            results.c_headers_fails.append('sched.h')
        elif not cc.has_function('sched_getaffinity', '', extra_args=c_flags)[0]:
            results.c_functions_fails.append('sched_getaffinity')

        for h in ["xlocale.h", "linux/futex.h", "endian.h", "dlfcn.h", "sys/shm.h", "cet.h",
                  "poll.h", "sys/inotify.h", "linux/udmabuf.h", "threads.h", "pthread_np.h"]:  # fmt: skip
            if not cc.check_header(h, '', extra_args=c_flags)[0]:
                results.c_headers_fails.append(h)

        if not cc.has_header_symbol("time.h", "struct timespec", "", extra_args=c_flags)[0]:  # fmt: skip
            results.c_header_symbols_fails['time.h'] = ['"struct timespec"']

        if not cc.has_header_symbol("errno.h", "program_invocation_name", "", extra_args=c_flags)[0]:  # fmt: skip
            results.c_header_symbols_fails['errno.h'] = ['program_invocation_name']

        if not cc.has_function('posix_memalign', '', extra_args=c_flags)[0]:
            results.c_functions_fails.append('posix_memalign')

        if not cc.has_members("struct dirent",["d_type"],  # noqa
                              prefix=DIRENT_HAS_D_TYPE_PREFIX,
                              extra_args=c_flags)[0]:  # fmt: skip
            results.c_members_fails['struct dirent'] = ['d_type']

        if not cc.links("int main() { return 0; }", extra_args=["-Wl,-Bsymbolic"] + c_flags)[0]:  # fmt: skip
            results.c_links_fails.append('Bsymbolic')

        if not cc.links(XLOCALE_CODE, extra_args=c_flags)[0]:
            results.c_links_fails.append('xlocale')

        if not cpp.links(GNU_QSORT_R_CODE, extra_args=cpp_flags)[0]:
            results.cpp_links_fails.add('qsort_r')

        if not cpp.links(BSD_QSORT_R_CODE, extra_args=cpp_flags)[0]:
            results.cpp_links_fails.add('qsort_r')

        functions_to_detect: T.List[T.Tuple[str, str, T.Optional[T.Callable[[], bool]]]] = [
            ('strtof', '', None),
            ('mkostemp', '', None),
            ('memfd_create', '#include <sys/mman.h>', None),
            ('flock', '', None),
            ('strtok_r', '', None),
            ('getrandom', '', None),
            ('qsort_s', '', None),
            ('posix_fallocate', '', None),
            ('secure_getenv', '', None),
            ('sysconf', '#include <unistd.h>', None),
            ('thrd_create', '#include <threads.h>', lambda: 'threads.h' in results.c_headers_fails),
            ('pthread_setaffinity_np', '#include <pthread.h>', None),
            ('reallocarray', '', None),
            ('fmemopen', '', None),
            ('dladdr', '', None),
            ('dl_iterate_phdr', '', None),
            ('clock_gettime', '', None),
            ('__builtin_add_overflow', '', None),
            ('__builtin_add_overflow_p', '', None),
            ('__builtin_sub_overflow_p', '', None),
            ('__builtin_arm_get_fpscr', '', None),
            ('__builtin_arm_set_fpscr', '', None),
            ('__builtin_aarch64_get_fpcr', '', None),
            ('__builtin_aarch64_set_fpcr', '', None),
        ]

        for f, prefix, check in functions_to_detect:
            if check and check():
                results.c_functions_fails.append(f)
                continue
            if not cc.has_function(f, prefix, extra_args=c_flags)[0]:
                results.c_functions_fails.append(f)

        if not cc.has_multi_link_arguments(['-Wl,--build-id=sha1'])[0]:
            results.c_supported_link_arguments_fails.append('-Wl,--build-id=sha1')

        if cc.get_argument_syntax() != 'msvc':
            _trial_c = [
                '-Werror=implicit-function-declaration',
                '-Werror=missing-prototypes',
                '-Werror=return-type',
                '-Werror=empty-body',
                '-Werror=gnu-empty-initializer',
                '-Werror=incompatible-pointer-types',
                '-Werror=int-conversion',
                '-Werror=pointer-arith',
                '-Werror=vla',
                '-Wimplicit-fallthrough',
                '-Wmisleading-indentation',
                '-Wno-missing-field-initializers',
                '-Wno-format-truncation',
                '-fno-math-errno',
                '-fno-trapping-math',
                '-Qunused-arguments',
                '-fno-common',
                '-Wno-initializer-overrides',
                '-Wno-override-init',
                '-Wno-unknown-pragmas',
                '-Wno-microsoft-enum-value',
                '-Wno-unused-function',
                '-Wno-nonnull-compare',
                '-Werror=format',
                '-Wformat-security',
                '-Werror=thread-safety',
                '-ffunction-sections',
                '-fdata-sections',
            ]
            _trial_cpp = [
                '-fdata-sections',
                '-ffunction-sections',
                '-flifetime-dse=1',
                '-fno-math-errno',
                '-fno-trapping-math',
                '-fno-exceptions',
                '-fno-rtti',
                '-Qunused-arguments',
                '-Werror=empty-body',
                '-Werror=format',
                '-Werror=gnu-empty-initializer',
                '-Werror=pointer-arith',
                '-Werror=return-type',
                '-Werror=vla',
                '-Wformat-security',
                '-Wmisleading-indentation',
                '-Wno-address-of-temporary',
                '-Wno-array-bounds',
                '-Wno-c++11-narrowing',
                '-Wno-c99-designator',
                '-Wno-class-memaccess',
                '-Wno-format-truncation',
                '-Wno-microsoft-enum-value',
                '-Wno-missing-braces',
                '-Wno-missing-field-initializers',
                '-Wno-narrowing',
                '-Wno-non-virtual-dtor',
                '-Wno-pointer-arith',
                '-Wno-reorder-init-list',
                '-Wno-sign-compare',
                '-Wno-switch',
                '-Wno-unknown-pragmas',
                '-Wno-unused-function',
                '-Wno-vla-cxx-extension',
                '-Wno-writable-strings',
                '-Wno-write-strings',
            ]
            for arg in _trial_c:
                args = [arg] if arg.startswith('-Werror=') else ['-Werror', arg]
                if not cc.has_multi_arguments(args)[0]:
                    results.c_supported_arguments_fails.append(arg)
            for arg in _trial_cpp:
                args = [arg] if arg.startswith('-Werror=') else ['-Werror', arg]
                if not cpp.has_multi_arguments(args)[0]:
                    results.cpp_supported_arguments_fails.append(arg)

        return results
