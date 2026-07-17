## Added support for the QNX qcc/q++ compiler driver

Meson can now detect and use `qcc` and `q++`, the C and C++ compiler
drivers shipped with the QNX Software Development Platform (SDP), via new
`QccCCompiler`/`QccCPPCompiler` classes (compiler id `qcc`), and generally
recognizes QNX as a target platform via `MachineInfo.is_qnx()`.

This file is a compendium of the QNX/qcc-specific adaptations across the
codebase: what was changed, where, and why. It exists because most of the
reasoning behind these adaptations (confirmed against a real QNX 8.0 SDP,
and re-verified end to end - detection, cross-compilation, dependency
files, LTO, coverage, OpenMP, PGO, sanitizers - against a real QNX SDP 7.1
install) doesn't belong as inline source comments.

**Driver architecture**

qcc (C) and q++ (C++) are QNX SDP's own compiler drivers: they parse the
command line and invoke `cc1`/`cc1plus` (genuine, unmodified GCC/G++
codegen backends), the assembler, and the linker directly, rather than
wrapping a separate gcc/g++ driver binary. See:
<https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/q/qcc.html>

Consequence: flags implemented by cc1/cc1plus/cpp itself (`-c`, `-o`,
`-I`, `-isystem`, `-D`, `-U`, `-O`, `-g`, `-std=`, `-E`, `-x`,
`-nostdinc[++]`, `-W{p,c,a,l},arg`, `-flto=auto`/`-flto=N`, and any other
`-m`/`-f` flag) behave exactly as with plain gcc/g++. Flags GCC's *driver*
implements are a different story - qcc's own driver doesn't necessarily
replicate them, which is the source of nearly every override below.

`QccCCompiler`/`QccCPPCompiler` (`mesonbuild/compilers/c.py`,
`mesonbuild/compilers/cpp.py`) mix `QccCompiler`
(`mesonbuild/compilers/mixins/qcc.py`) in *ahead of*
`GnuCCompiler`/`GnuCPPCompiler`, so MRO prefers these overrides while
still inheriting the cc1/cc1plus-level behavior qcc genuinely shares with
gcc. `-std=` remapping in `cpp.py` includes `qcc` in its supported-id set
for the same reason: q++'s cc1plus is unmodified GCC, so it's exactly as
GCC-compatible as plain `gcc` there.

**Detection (`mesonbuild/compilers/detect.py`)**

- qcc/q++ have no distinguishing version-banner text (no "Free Software
  Foundation" string of their own), so they're recognized by driver
  executable name (`qcc`/`q++`/`qcc.exe`/`q++.exe`) instead, and routed to
  `QccCCompiler`/`QccCPPCompiler` rather than a plain `Gnu*Compiler`.
- Unlike plain gcc, qcc/q++ refuse to run `-Wl,--version` (used to probe
  the linker) without a source file (`cc: no files to process`). Detection
  creates an empty temp source file and passes it as `extra_args` to
  `guess_nix_linker()` to satisfy the driver, then removes it. The temp
  path is tracked separately rather than re-inspected from `extra_args`
  afterward, because `guess_nix_linker()` mutates that list in place.
- On native QNX, `qcc`/`q++` are tried first in the default compiler
  search list, falling back to `cc`/`gcc`/`clang`. On a QNX 8.0 Self-Hosted
  Developer Desktop, qcc/q++ aren't actually shipped by default (only
  clang, with `gcc`/`g++` as shims to it), so this falls through
  harmlessly. This has no effect on cross-compiling *for* QNX - Meson
  always requires cross compilers to be named explicitly in the cross
  file's `[binaries]` section (see the example below).

**Dependency-file generation**

`QccCompiler.get_dependency_gen_args()` (`mixins/qcc.py`). Plain `-M`
means "generate a linker mapfile" for qcc, colliding with GCC's meaning,
so `GnuLikeCompiler`'s `['-MD', '-MQ', outtarget, '-MF', outfile]` can't
be passed directly. The flags are instead routed through the `-Wc,`
compile-phase passthrough to cc1/cc1plus:

```
['-Wc,-MQ,' + outtarget, '-Wc,-MMD', '-Wc,-MP', '-Wc,-MF,' + outfile]
```

Two caveats found in the process:

- `-MD`/`-MMD` immediately followed by `-MF <file>` crashes cc1 itself
  ("too many filenames given") - a genuine QNX cc1 bug, reproduced
  invoking cc1 directly. Any flag between them avoids it; `-MP` is
  included for exactly that reason (it also happens to be independently
  useful - see below).
- `-MP`'s phony header rules aren't actually emitted by this cc1 (unlike
  stock gcc), so deleting a header may leave a stale dependency-file entry
  until a clean rebuild. A narrow, currently-unfixed gap.

`-MQ` matches `GnuLikeCompiler`'s default and correctly
escapes make-special characters (e.g. spaces) in `outtarget`.

**Preprocess-only output**

`QccCompiler.get_preprocess_only_args()` (`mixins/qcc.py`) returns
`['-E', '-Wp,-P']` instead of `['-E', '-P']`. qcc's driver silently drops
bare `-P` *and* redirects cc1's output from stdout to a derived
`<source>.i` file on disk instead of suppressing line markers - it
hijacks the whole output channel, not just cosmetics. This matters beyond
cosmetics because `Compiler.get_compiler_args_for_mode()` uses this flag
set for `CompileCheckMode.PREPROCESS`, which `get_define()`/
`has_define()` rely on reading from stdout; uncorrected, this silently
broke those on qcc/q++. `-Wc,` (used elsewhere in the mixin) does not
work here - it reaches a different phase and still leaves line markers in
place; `-Wp,` (the preprocessor-phase passthrough) does.
`GnuLikeCompiler.get_preprocess_to_file_args()` builds on this method, so
the fix carries through automatically.

**Link-time optimization**

Plain LTO (`b_lto`) needs no override: `GnuCompiler`'s own
`-flto=auto`/`-flto=<threads>` generation works unmodified on qcc and
q++, producing genuine cross-translation-unit inlining and constant
propagation.

ThinLTO's incremental cache is the one part that's broken:
`QccCompiler.get_thinlto_cache_args()` raises `EnvironmentException`
instead of emitting `-flto-incremental=<path>` (added by
`GnuCompiler.get_lto_compile_args()` whenever `b_thinlto_cache` is
enabled), because cc1 rejects it outright as an unrecognized option.
Better to fail the build clearly than let `b_thinlto_cache` silently
break an otherwise-working `b_lto` build.

**Alternate linker selection**

`QccCompiler.use_linker_args()` (`mixins/qcc.py`) raises `MesonException`
when an alternate linker is requested via the `[binaries]` `c_ld`/`cpp_ld`
machine-file entry (**not** a `-D` build option - `c_ld`/`cpp_ld` have no
such option; see `docs/markdown/Machine-files.md`), e.g.:

```ini
[binaries]
c_ld = 'lld'
```

`-fuse-ld=` reaches cc1/cc1plus, which never invoke a linker themselves,
so it has no effect either way, and QNX documents no qcc-specific
linker-selection mechanism.

**Coverage instrumentation**

`QccCompiler.get_coverage_args()`/`get_coverage_link_args()`
(`mixins/qcc.py`) return `['-fprofile-arcs', '-ftest-coverage']` instead
of `--coverage` (used by `Compiler.get_coverage_link_args()`'s default,
which delegates to the linker), since `--coverage` is not a documented
qcc option at either compile or link time - though the `-f`-prefixed
flags it expands to in real GCC are. This matches QNX's own
`buildconfig_add_debug_instcode` docs and links `libgcov.a` with working
gcov symbols.

**Runtime auto-linking gaps (OpenMP, PGO, sanitizers)**

Real gcc's *driver* auto-links a matching runtime library whenever
`-fopenmp`, `-fprofile-generate`, or `-fsanitize=<name>` appears at link
time, via its own internal spec files. qcc's driver does not replicate
this - each compiles fine but fails to link with undefined
`GOMP_*`/`__gcov_*`/`__asan_*`/`__ubsan_*` references (the runtime
libraries themselves do exist in the SDP). Three separate overrides in
`mixins/qcc.py` compensate:

- `openmp_link_flags()` appends `-lgomp` to `self.openmp_flags()`.
- `get_profile_generate_args()` returns
  `['-fprofile-generate', '-fprofile-arcs']` (used at both compile and
  link time, so one fixed value covers both). `-fprofile-use`/`b_pgo=use`
  needs no equivalent fix.
- `sanitizer_link_args()` appends `-l<runtime>` per the
  `_SANITIZER_RUNTIME_LIBS` map (`address`→`asan`, `undefined`→`ubsan`,
  `leak`→`lsan`). `-static-libasan` is rejected outright as an unknown
  qcc option, so only the shared runtime can be linked here - the usual
  gcc static-sanitizer workaround isn't available. It also force-keeps
  `-lc` (via a `-Wl,--no-as-needed`/`-Wl,--as-needed` bracket) whenever a
  runtime is linked: on SDP 8.0, the sanitizer runtimes pull in
  `libgcc_eh.a`, whose `__gthread_once` references `pthread_once`, and a
  shared-library target with no other pthread-touching code has nothing
  else marking libc as needed yet - so plain `-lc` placed after the
  `-Wl,--as-needed` Meson already emits gets silently dropped, and the
  link fails with an undefined `pthread_once` (confirmed against a real
  SDP 8.0 `shared_library()` target; SDP 7.1's gcc 8.3.0 backend doesn't
  hit this). Bracketing with `--no-as-needed` keeps `-lc` regardless of
  link-line order.

  **Which of these runtimes actually ship is SDP-version/target-dependent,
  not just a qcc/Meson property** - confirmed by diffing two real installs
  side by side: SDP 8.0 (`~/qnx800`, gcc 12.2.0 backend) ships
  `libasan`/`liblsan`/`libubsan` (no `libtsan`) for its x86_64 target, and
  `-Db_sanitize=address` builds and links cleanly there. SDP 7.1
  (`~/qnx710`, gcc 8.3.0 backend) ships **only `libubsan`** for the same
  x86_64 target - no `libasan`, `liblsan`, or `libtsan` at all.
  `-Db_sanitize=address`/`=leak` therefore compile fine but fail to link
  there (`cannot find -lasan`/`-llsan`); `-Db_sanitize=undefined` works on
  both. This isn't a bug in the flag generation (it's exactly what real
  gcc would need too), just a gap in the older SDP's shipped runtimes.
  Check `$QNX_TARGET/<arch>/lib/lib{asan,ubsan,lsan,tsan}.so` for your
  specific SDP/target before relying on a given sanitizer.

**Default include directories**

`QccCompiler.get_default_include_dirs()` (`mixins/qcc.py`) queries with
`-vv` instead of `GnuLikeCompiler`'s default `-v`: qcc/q++ print no
banner for plain `-v`, so double-verbose is required to get the include
search path listing. `mixins/gnu.py`'s
`gnulike_default_include_dirs()` gained a `verbosity_arg` parameter to
support this.

**Sanity-check command construction**

`QccCompiler._sanity_check_compile_args()` (`mixins/qcc.py`) builds a
clean, single-inclusion, mode-consistent sanity-check command instead of
reusing the base/`CLikeCompiler` combination's command. That default
layers a second, independently-fetched copy of external cargs (and, for
cross builds without an exe wrapper, `-c`) on top of
`Compiler._sanity_check_compile_args()`'s own already link-shaped command
(`-o <exe> <source>` plus linker flags) - so the final invocation can end
up with `-c` mixed into a command that also names a linked `.exe` output
and carries linker `-l` flags, plus duplicated flags throughout. gcc/clang
tolerate this (redundant flags are harmless noise; unused `-l` flags
under `-c` are simply ignored), but qcc's own driver rejects it outright
("Can't specify ... -c ... with -o and have multiple files"). The
override keeps compile-only and link-shaped modes mutually exclusive,
matching how a real compile/link is always split into two separate qcc
invocations elsewhere in Meson.

**Sanity-check licensing hint**

`QccCompiler.sanity_check()` (`mixins/qcc.py`) wraps sanity-check
failures with a hint about `qnxsdp-env.sh` and QNX SDP license
validation. qcc/q++ do their own license validation and exit 129-133 on
failure, and a missing/expired/unactivated license is a common cause of
qcc/q++ failing to run at all.

`qnxsdp-env.sh` lives under the SDP install root and must be *sourced*
(not just run) into the current shell, since it works by exporting
`QNX_HOST`/`QNX_TARGET`/`PATH`/etc. into the calling environment - e.g.
for SDP 7.1 installed at the default location:

```sh
. ~/qnx710/qnxsdp-env.sh
```

The exact path is SDP-version- and install-location-dependent (e.g.
`~/qnx800/qnxsdp-env.sh` for SDP 8.0), which is why the sanity-check
hint above names the script generically rather than a specific path.

**`--print-search-dirs` / system include and lib dirs**

`Environment.get_compiler_system_lib_dirs()` (`environment.py`)
deliberately excludes `qcc` from the id set it queries via
`-print-search-dirs`: that flag isn't a documented qcc option, and unlike
the graceful `[]` this function falls back to for unsupported compilers,
it raises on a non-zero exit code - including qcc here risks a hard
failure. `get_compiler_system_include_dirs()`, by contrast, does include
`qcc` alongside `gcc`/`clang`, since its query (`get_default_include_dirs()`,
a compile-phase flag) qcc genuinely supports.

**C++20 named modules (q++ only, unfixed)**

On SDP 8.0 (gcc 12.2.0 backend), q++'s driver silently no-ops on a
module-interface-unit source file (`.cppm`/`.ixx`) - exit 0, cc1plus
never invoked (per `-v`), no output file produced - while an ordinary
`.cpp` file compiles fine with the same `-fmodules-ts` flag. This is
source-suffix dispatch done by gcc's *driver* before cc1plus ever sees
the file, so unlike the flag-level gaps above there is no
flag-passthrough trick (`-Wc,` or otherwise) to work around it, and no
single method in `QccCompiler`'s surface gates "is this source file
compilable" for Meson to hook a guard into. This section is the only
record of the gap; there is no code-level mitigation.

SDP 7.1 (gcc 8.3.0 backend) is worse, not just older: q++'s cc1plus
there rejects `-fmodules-ts` outright as an unrecognized command-line
option on *any* C++ source, `.cppm`/`.ixx` or plain `.cpp` alike (hard
compile error, not the SDP 8.0 driver-level silent no-op) - confirmed
directly against the real SDP 7.1 install, with and without
`-std=c++2a`. Separately, `-fmodules` (without `-ts`, a Modula-2-only
flag that stock upstream g++ merely warns about and ignores for C++) is
hard-rejected by cc1plus as unrecognized on *both* SDP 7.1 and SDP 8.0.
Meson itself never passes either flag automatically - `GnuCPPCompiler.
get_cpp_modules_args()` (`['-fmodules', '-fmodules-ts']`, inherited
unmodified here) is only consulted by `should_use_dyndeps_for_target()`
to detect whether a *user*-supplied `cpp_args` entry warrants enabling
Ninja's C++-modules dyndeps scanning - so this only bites a project that
explicitly opts into C++ modules on qcc/q++ via `cpp_args`.

**Threading (`-pthread`)**

Not handled in `QccCompiler` at all - it's a property of the target
platform, not of qcc/q++. QNX Neutrino's libc always includes pthreads
regardless of which compiler targets it (qcc/q++ merely document
`-pthread` as an ignored no-op warning), so Meson skips `-pthread`/
`-lpthread` for **any** compiler or linker targeting QNX, via
`MachineInfo.is_qnx()`:

- `CLikeCompiler.thread_flags()` (`mixins/clike.py`)
- `GnuLikeDynamicLinkerMixin.thread_flags()` (`linkers/linkers.py`)

This also covers non-GCC-family compilers and non-qcc/q++ toolchains
targeting QNX.

**Symbol extraction (`mesonbuild/scripts/symbolextractor.py`)**

QNX ships real GNU binutils (`ntox86_64-ar`, GNU `ld.bfd`, etc.), so a
native/self-hosted QNX build now uses the same readelf/nm-based
`gnu_syms()` extraction as Linux/Hurd/Haiku (`mesonlib.is_qnx()` added to
the dispatch condition), avoiding unnecessary relinks when a shared
library's exported symbols haven't changed. Previously this fell through
to `dummy_syms()`, which forces a relink unconditionally.

**JNI dependency (`mesonbuild/dependencies/dev.py`)**

`JNISystemDependency`'s machine-info-to-platform-include-dir mapping
gained a `qnx` → `'qnx'` case. JNI's `jni_md.h` (defining ABI-specific
bits like `JNIEXPORT`/`JNICALL` and `jint`/`jlong` sizes) lives in a
per-OS subdirectory of a JDK's `include/` dir, named after the OS the JDK
was built for; a QNX-targeting JDK uses `qnx` for this, matching the
lowercase-OS-name convention used for every other platform in that
mapping.

**Cross-compiling for QNX**

Point a cross file's `[binaries]` section at qcc/q++ including the
required `-V` target selector, and declare `system = 'qnx'` in
`[host_machine]` (this is also what makes Meson skip `-pthread` - see
above), for example:

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
