---
short-description: Notes and known issues for specific platforms
...

# Platform notes

This page collects information that is specific to a platform or to a toolchain.

## macOS deployment target

Programs can be compiled for older macOS versions than the one they are compiled on.  The
version of the build machine therefore does not tell which functions are available when the
program runs.

The deployment target is chosen by the compiler.  Either set the `MACOSX_DEPLOYMENT_TARGET`
environment variable before running Meson, or pass `-mmacosx-version-min` in both the compile
and the link arguments, for example in a native file:

```ini
[built-in options]
c_args = ['-mmacosx-version-min=10.11']
c_link_args = ['-mmacosx-version-min=10.11']
```

The checks that Meson runs use the same arguments, so they see the deployment target.

When detecting a function with `compiler.has_function()`, specify the header that declares it
in the `prefix` argument.  For example, `open_memstream` was introduced in macOS 10.13.  When
building on macOS 10.13 for macOS 10.11, the following check correctly reports the function as
missing:

```meson
cc.has_function('open_memstream', prefix : '#include <stdio.h>')
```

Without the header, the check lacks the availability information and incorrectly reports the
function as available.

## AIX and IBM i

Meson supports AIX with the GCC and OpenXL compilers.  IBM i is supported in the PASE
environment, which uses the AIX user space.  On both, `host_machine.system()` returns `'aix'`.
`host_machine.kernel()` returns `'aix'` or `'os400'` to tell them apart.

The AIX linker always links the whole contents of static libraries, so `link_with` is accepted
but has the same effect as `link_whole`.

## QNX

Meson can detect and use `qcc` and `q++`, the C and C++ compiler drivers shipped with the QNX
Software Development Platform (SDP).  For cross compilation, point the `[binaries]` section of
the cross file at `qcc` and `q++`, including the required `-V` target selector, and set
`system = 'qnx'` in `[host_machine]`:

```ini
[binaries]
c = ['qcc', '-Vgcc_ntoaarch64le']
cpp = ['q++', '-Vgcc_ntoaarch64le']

[host_machine]
system = 'qnx'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
```

The following limitations apply:

1. ThinLTO incremental cache does not work.  `-Db_thinlto_cache=true` raises an error at
   configure time, while `-Db_lto=true` is unaffected.
2. Alternate linker selection is not supported.  Setting `c_ld` or `cpp_ld` (for example to
   `lld` or `gold`) raises an error.
3. If a header is deleted, stale entries remain in the dependency files, because `-MP` does not
   emit phony header rules.  A clean build is needed to recover.
4. There is no static sanitizer runtime, so `-static-libasan` is rejected and only the shared
   runtime can be linked.
5. The available sanitizers depend on the SDP version.  SDP 7.1 only provides `libubsan`, so
   `-Db_sanitize=address` and `-Db_sanitize=leak` fail to link there.  SDP 8.0 adds asan and
   lsan.  `-Db_sanitize=undefined` works on both, and tsan is not available on either.
6. C++20 named modules do not work.  With SDP 8.0, `-fmodules-ts` compiles but silently ignores
   `.cppm` and `.ixx` files.  With SDP 7.1, `-fmodules-ts` is rejected for C++ sources.  Plain
   `-fmodules` is rejected on both.  This only affects projects that enable modules through
   `cpp_args`.
7. Relinking is avoided for unchanged shared libraries only on native QNX builds.  When
   cross compiling to QNX, shared libraries are always relinked.
