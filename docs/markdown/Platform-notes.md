---
short-description: Notes and known issues for specific platforms
...

# Platform notes

This page collects information that is specific to a platform or to a toolchain.

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
