## Added support for the QNX qcc/q++ compiler driver

Meson can now detect and use `qcc` and `q++`, the C and C++ compiler drivers shipped with the QNX Software Development Platform (SDP), and recognizes QNX as a target platform.

**Cross-compiling for QNX**

Point a cross file's `[binaries]` section at qcc/q++ including the
required `-V` target selector, and declare `system = 'qnx'` in
`[host_machine]`, for example:

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

Known Issues:
1. ThinLTO incremental cache doesn't work — -Db_thinlto_cache=true raises a clear error at configure time; plain -Db_lto=true is unaffected. -flto-incremental= is rejected outright by cc1.
2. No alternate linker selection — c_ld/cpp_ld in a cross/native file (e.g. 'lld', 'gold') raises MesonException. qcc's driver never invokes a separate linker binary itself, and QNX documents no equivalent mechanism.
3. Stale dependency-file entries after deleting a header — -MP's phony-header rules aren't emitted by this cc1, unlike stock gcc. Narrow, unfixed; only shows up as a missed rebuild until a clean build.
4. No static sanitizer runtime — -static-libasan is rejected as unknown; only the shared sanitizer runtime can ever be linked.
5. Sanitizer runtime availability is SDP-version-dependent — SDP 7.1 ships only libubsan (no asan/lsan/tsan at all), so -Db_sanitize=address/=leak fail to link there; SDP 8.0 adds asan/lsan (still no tsan on either SDP). =undefined works on both.
6. C++20 named modules are broken, differently per SDP — SDP 8.0: -fmodules-ts compiles but silently no-ops on .cppm/.ixx files (no code-level fix possible — it's driver-level source-suffix dispatch before cc1plus ever runs). SDP 7.1: worse — -fmodules-ts itself is hard-rejected as unrecognized on any C++ source. Plain -fmodules is hard-rejected on both SDPs. Only bites a project that explicitly opts into modules via cpp_args.
7. Symbol-extraction relink-avoidance only applies natively — the gnu_syms() optimization (skip relinking when a shared library's exported symbols haven't changed) only kicks in for a native/self-hosted QNX build; cross-compiling to QNX from another host (the SDP's primary use case) always falls back to unconditional relinking, same as before this work.
