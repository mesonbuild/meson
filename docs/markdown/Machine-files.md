# Cross and Native File reference

Cross and native files are nearly identical, but not completely. This
is the documentation on the common values used by both, for the
specific values of one or the other see the [cross
compilation](Cross-compilation.md) and [native
environments](Native-environments.md).

*Changed in 0.56.0* Keys within sections are now case sensitive. This
is required to make project options work correctly.

## Data Types

There are four basic data types in a machine file:
- strings
- arrays
- booleans
- integers

A string is specified single quoted:
```ini
[section]
option1 = 'false'
option2 = '2'
```

An array is enclosed in square brackets, and must consist of strings or booleans
```ini
[section]
option = ['value']
```

A boolean must be either `true` or `false`, and unquoted.
```ini
option = false
```

An integer must be an unquoted numeric constant.
```ini
option = 42
```

## Sections

The following sections are allowed:
- constants
- binaries
- paths
- properties
- cmake
- project options
- built-in options

### constants

*Since 0.56.0*

String and list concatenation is supported using the `+` operator,
joining paths is supported using the `/` operator. Entries defined in
the `[constants]` section can be used in any other section (they are
always parsed first), entries in any other section can be used only
within that same section and only after it has been defined.

```ini
[constants]
toolchain = '/toolchain'
common_flags = ['--sysroot=' + toolchain / 'sysroot']

[properties]
c_args = common_flags + ['-DSOMETHING']
cpp_args = c_args + ['-DSOMETHING_ELSE']

[binaries]
c = toolchain / 'gcc'
```

This can be useful with cross file composition as well. A generic
cross file could be composed with a platform specific file where
constants are defined:

```ini
# aarch64.ini
[constants]
arch = 'aarch64-linux-gnu'
```

```ini
# cross.ini
[binaries]
c = arch + '-gcc'
cpp = arch + '-g++'
strip = arch + '-strip'
pkg-config = arch + '-pkg-config'
...
```

This can be used as `meson setup --cross-file aarch64.ini --cross-file
cross.ini builddir`.

Note that file composition happens before the parsing of values. The
example below results in `b` being `'HelloWorld'`:

```ini
# file1.ini:
[constants]
a = 'Foo'
b = a + 'World'
```

```ini
#file2.ini:
[constants]
a = 'Hello'
```

The example below results in an error when file1.ini is included
before file2.ini because `b` would be defined before `a`:

```ini
# file1.ini:
[constants]
b = a + 'World'
```

```ini
#file2.ini:
[constants]
a = 'Hello'
```

*Since 1.3.0* Some tokens are replaced in the machine file before parsing it:
- `@GLOBAL_SOURCE_ROOT@`: the absolute path to the project's source tree
- `@DIRNAME@`: the absolute path to the machine file's parent directory.

It can be used, for example, to have paths relative to the source directory, or
relative to toolchain's installation directory.
```ini
[binaries]
c = '@DIRNAME@/toolchain/gcc'
exe_wrapper = '@GLOBAL_SOURCE_ROOT@' / 'build-aux' / 'my-exe-wrapper.sh'
```

### Binaries

The binaries section contains a list of binaries. These can be used
internally by Meson, or by the `find_program` function.

These values must be either strings or an array of strings

Compilers and linkers are defined here using `<lang>` and `<lang>_ld`.
`<lang>_ld` is special because it is compiler specific. For compilers
like gcc and clang which are used to invoke the linker this is a value
to pass to their "choose the linker" argument (-fuse-ld= in this
case). For compilers like MSVC and Clang-Cl, this is the path to a
linker for Meson to invoke, such as `link.exe` or `lld-link.exe`.
Support for `ld` is *new in 0.53.0*

*changed in 0.53.1* the `ld` variable was replaced by `<lang>_ld`,
because it regressed a large number of projects. in 0.53.0 the `ld`
variable was used instead.

Native example:

```ini
c = '/usr/bin/clang'
c_ld = 'lld'
sed = 'C:\\program files\\gnu\\sed.exe'
llvm-config = '/usr/lib/llvm8/bin/llvm-config'
```

Cross example:

```ini
c = ['ccache', '/usr/bin/i586-mingw32msvc-gcc']
cpp = ['ccache', '/usr/bin/i586-mingw32msvc-g++']
c_ld = 'gold'
cpp_ld = 'gold'
ar = '/usr/i586-mingw32msvc/bin/ar'
strip = '/usr/i586-mingw32msvc/bin/strip'
pkg-config = '/usr/bin/i586-mingw32msvc-pkg-config'
```

An incomplete list of internally used programs that can be overridden
here is:

- cmake
- cups-config
- gnustep-config
- gpgme-config
- libgcrypt-config
- libwmf-config
- llvm-config
- pcap-config
- pkg-config
- sdl2-config
- wx-config (or wx-3.0-config or wx-config-gtk)

#### Per-binary interpreter (POSIX only)

For hermetic-toolchain builds where bundled binaries need a dynamic
loader prefix (for example `ld-linux --library-path <dir>`) to find
their shared libraries, you can declare an `interpreter` for any
`[binaries]` entry using a dotted key:

```ini
[binaries]
perl = '/opt/toolchain/bin/perl'
python3_codegen = '/opt/py36/bin/python3.6'
python3_codegen.interpreter = ['/opt/py36/lib/ld.so', '--library-path', '/opt/py36/lib']

[properties]
# Global default applied to any [binaries] entry that does not have its
# own `<name>.interpreter` set.
interpreter = ['/opt/toolchain/lib/ld-linux.so', '--library-path', '/opt/toolchain/lib']
```

Resolution order:

1. Per-binary `<name>.interpreter` under `[binaries]`.
2. Global `interpreter` under `[properties]`.
3. Otherwise, the binary is invoked bare.

When an interpreter applies to an entry, Meson materializes a POSIX
shell wrapper at `<builddir>/meson-private/binary-wrappers/<name>` that:

- Prepends the wrappers directory to `PATH` (so the wrapper appears
  on `PATH` for downstream tools that re-launch by name).
- `exec`s the interpreter on the bare binary plus any trailing argv
  from a list-form `[binaries]` entry (e.g. `python = ['/path/python', '-B']`
  becomes `exec <interp> /path/python -B "$@"`), forwarding remaining
  arguments via `"$@"`.

The wrapper deliberately does NOT export `LD_LIBRARY_PATH`.  The
interpreter's `--library-path` argument is honored by `ld-linux.so`
both at process startup AND for subsequent `dlopen()` calls inside the
wrapped process (the loader's search path is shared with libdl).
Keeping `LD_LIBRARY_PATH` out of the wrapper's environment prevents
the hermetic libdir from leaking to subprocesses (e.g. python -> gcc)
that should resolve against the host glibc instead.  When per-binary
environment is needed (e.g. `PERL5LIB=...`), include `env VAR=VAL ...`
as a prefix in the interpreter list: `perl.interpreter = ['env',
'PERL5LIB=/p', '/loader', '--library-path', '/libs']`.

`ExternalProgram.command` is then a single-element list pointing at
the wrapper, so positional-argument call sites (e.g. `find_program`)
work without splatting.

Setting `<name>.interpreter = []` disables the global `[properties]
interpreter` default for this entry: `lookup_binary_interpreter` returns
the empty list, and the wrapper-generation call site treats that as "no
interpreter applies", so the bare binary is used directly (see
`mesonbuild/environment.py:lookup_binary_interpreter` and
`mesonbuild/programs.py:ExternalProgram.from_entry`).

The wrapper uses the bundled loader's `--argv0` flag to propagate the
wrapper's own path as `argv[0]` to the wrapped binary (so child processes
that re-launch by name -- e.g. CPython exec'ing `sys.executable` -- enter
through the wrapper and inherit the loader prefix transparently).  This
requires `--argv0` support in the loader, which was added in glibc 2.33;
earlier loaders will not honor the flag and the wrapped binary will see
the loader path as `argv[0]` instead.

This feature is POSIX-only.  On Windows the property is silently
ignored with a one-time warning, since DLL resolution does not use a
dynamic-loader prefix.

### compilers

*New in 1.12.0*

The `[compilers]` section allows declaring compiler configuration explicitly,
rather than relying on Meson to auto-detect it from a binary. This is primarily
useful for hermetic toolchains where the compiler and its subprograms require a
custom execution environment that is not present on the host system.

When a language is declared in this section:

- If `<lang>.type` is set, Meson skips family detection and uses that type directly.
- If `<lang>.version` is also set, Meson skips version detection entirely and uses
  the declared version. When `<lang>.version` is omitted, Meson still runs the
  binary with `--version` to determine the version.

The compiler binary itself is always specified via `<lang>` in the `[binaries]`
section.

Each key is prefixed with the language identifier (`c.`, `cpp.`, etc.).

#### Keys

| Key | Type | Description |
|-----|------|-------------|
| `<lang>.type` | string | Compiler family. Supported values: `'gcc'`, `'clang'`, `'clang-cl'`, `'msvc'`, `'intel'` (Classic icc/icpc), `'intel-llvm'` (oneAPI icx/icpx), `'arm'` (Arm Compiler 5 armcc), `'armclang'` (Arm Compiler 6), `'pgi'` (NVIDIA HPC/PGI nvc/nvc++), `'emscripten'`. |
| `<lang>.version` | string | Version string (e.g. `'10.3.0'`). When specified, used in place of `--version` output. When omitted, Meson runs the binary with `--version` and parses the result as usual. |
| `<lang>.ccache` | bool | Whether to use ccache when invoking this compiler. Default: `true`. When `true`, ccache is used if found on `PATH`; the build proceeds without caching if ccache is not present. Set to `false` to disable caching unconditionally. |
| `<lang>.sysroot` | string | Override the root directory for the target system's headers and libraries. Has no effect on compilers that do not support a sysroot concept. |
| `<lang>.no-default-includes` | bool | Suppress the compiler's built-in system include search. Default: `false`. When set, the compiler's default system include directories are not searched; use `system-include-dirs` to specify them explicitly. Has no effect on compilers that have no equivalent flag (a warning is emitted). |
| `<lang>.system-include-dirs` | array | System include directories. When set alongside `no-default-includes`, these directories are the only system include directories searched. When set without `no-default-includes`, these directories are searched in addition to the compiler's defaults. |
| `<lang>.tool-search-paths` | array | Directories in which to search for compiler subtools (assembler, linker helpers, etc.). When omitted, the compiler uses its default search. |

To run compiler subprograms through a dynamic-loader prefix, set
`<lang>.interpreter` under the `[binaries]` section (see
[Per-binary interpreter](#per-binary-interpreter-posix-only)).  When such an
interpreter is configured for a GCC- or clang-family `<lang>`, Meson generates
per-subprogram wrappers under `<builddir>/meson-private/compiler-wrappers/<lang>/`
and passes `-B<that-dir>` to the compiler so its driver finds the wrapped
subprograms.

The wrapped subprograms depend on the compiler family:

- **GCC**: `cc1`, `cc1plus`, `lto1`.  These are dispatched by the gcc driver
  for preprocessing / compilation / link-time optimization.
- **clang**: `as`, `ld`.  Clang is monolithic for codegen (no separate `cc1`)
  and only dispatches the assembler / linker through `-B<prefix>`; the wrappers
  apply when `-fno-integrated-as` or an external linker is used.

#### Flag translation by compiler family

`—` means the key is not applicable for this compiler family.
`no-op` means the key is accepted but has no effect.

| Key | GCC, Clang | Intel Classic, Intel oneAPI, ARM 6 (armclang), Emscripten | MSVC, Clang-CL |
|-----|------------|-----------------------------------------------------------|----------------|
| `sysroot` | `--sysroot=<path>` | `--sysroot=<path>` (NVIDIA HPC/PGI: —) | — |
| `no-default-includes` | `-nostdinc` | `-nostdinc` | `/X` |
| `system-include-dirs` | `-isystem <dir>` | `-isystem <dir>` | `/imsvc <dir>` |
| `tool-search-paths` | `-B <dir>` | warning, ignored | warning, ignored |
| `ccache` | wraps invocation with ccache if available | wraps invocation with ccache if available | wraps invocation with ccache if available |

Notes:
- **NVIDIA HPC/PGI** (`nvc`/`nvc++`): otherwise identical to the Intel/ARM 6/Emscripten column but does not expose a sysroot concept; `sysroot` is silently ignored.
- **Clang-CL**: the MSVC-compatible Clang frontend. Uses MSVC-style flags (`/X`, `/imsvc`) matching its `cl.exe` compatibility mode; `--sysroot` and `-B` are not meaningful in this mode.
- **ARM Compiler 5** (`armcc`): a legacy proprietary compiler with its own flag dialect. None of the structured keys translate to equivalent armcc flags. A warning is emitted at setup for each key that is set; all are ignored. Use `[binaries]` and `[built-in options]` to pass armcc-specific flags directly.

#### Example: hermetic GCC toolchain

A self-contained GCC 12.2.0 toolchain bundled with the project under `sdk/`.
The `cc1` and `cc1plus` subprograms require shared libraries from `sdk/runtime/lib64`
that are not installed on the build host.

```ini
[constants]
_sdk     = '@GLOBAL_SOURCE_ROOT@' / 'sdk'
_gcc     = _sdk / 'gcc-12.2.0'
_runtime = _sdk / 'runtime'    # ELF loader and companion shared libraries

[binaries]
c   = _gcc / 'bin' / 'x86_64-linux-gnu-gcc'
cpp = _gcc / 'bin' / 'x86_64-linux-gnu-g++'
c.interpreter   = [_runtime / 'lib64' / 'ld-linux-x86-64.so.2',
                   '--library-path', _runtime / 'lib64']
cpp.interpreter = c.interpreter

[compilers]
c.type    = 'gcc'
c.version = '12.2.0'

cpp.type    = 'gcc'
cpp.version = '12.2.0'
```

With this configuration:

- Compiler subprograms are located and invoked automatically through the bundled ELF
  loader; no manual wrapper scripts or `LD_LIBRARY_PATH` setup is needed.
- Include directories and subtool locations are discovered automatically from the
  compiler.
- Compilation is fully cacheable by ccache.

When cross-compiling or using a non-standard sysroot, the optional override keys
(`sysroot`, `no-default-includes`, `system-include-dirs`, `tool-search-paths`)
can be used to override the discovered values.

#### Example: Clang with custom sysroot

```ini
[binaries]
c   = '/path/to/clang-17/bin/clang'
cpp = '/path/to/clang-17/bin/clang++'

[compilers]
c.type    = 'clang'
c.version = '17.0.6'
c.sysroot             = '/path/to/sdk'
c.no-default-includes = true
c.system-include-dirs = ['/path/to/clang-17/lib/clang/17/include',
                          '/path/to/sdk/usr/include']

cpp.type    = 'clang'
cpp.version = '17.0.6'
cpp.sysroot             = c.sysroot
cpp.no-default-includes = true
cpp.system-include-dirs = c.system-include-dirs
```

### Paths and Directories

*Deprecated in 0.56.0* use the built-in section instead.

As of 0.50.0 paths and directories such as libdir can be defined in
the native and cross files in a paths section. These should be
strings.

```ini
[paths]
libdir = 'mylibdir'
prefix = '/my prefix'
```

These values will only be loaded when not cross compiling. Any
arguments on the command line will override any options in the native
file. For example, passing `--libdir=otherlibdir` would result in a
prefix of `/my prefix` and a libdir of `otherlibdir`.

### Properties

*New in native files in 0.54.0*, always in cross files.

In addition to special data that may be specified in cross files, this
section may contain random key value pairs accessed using the
`meson.get_external_property()`, or `meson.get_cross_property()`.

*Changed in 0.56.0* putting `<lang>_args` and `<lang>_link_args` in
the properties section has been deprecated, and should be put in the
built-in options section.

#### Supported properties

This is a non exhaustive list of supported variables in the `[properties]`
section.

- `cmake_toolchain_file` specifies an absolute path to an already existing
  CMake toolchain file that will be loaded with `include()` as the last
  instruction of the automatically generated CMake toolchain file from Meson.
  (*new in 0.56.0*)
- `cmake_defaults` is a boolean that specifies whether Meson should automatically
  generate default toolchain variables from other sections (`binaries`,
  `host_machine`, etc.) in the machine file. Defaults are always overwritten
  by variables set in the `[cmake]` section. The default is `true`. (*new in 0.56.0*)
- `cmake_skip_compiler_test` is an enum that specifies when Meson should
  automatically generate toolchain variables to skip the CMake compiler
  sanity checks. This only has an effect if `cmake_defaults` is `true`.
  Supported values are `always`, `never`, `dep_only`. The default is `dep_only`.
  (*new in 0.56.0*)
- `cmake_use_exe_wrapper` is a boolean that controls whether to use the
  `exe_wrapper` specified in `[binaries]` to run generated executables in CMake
  subprojects. This setting has no effect if the `exe_wrapper` was not specified.
  The default value is `true`. (*new in 0.56.0*)
- `java_home` is an absolute path pointing to the root of a Java installation.
- `bindgen_clang_arguments` an array of extra arguments to pass to clang when
  calling bindgen
- `interpreter` is a list of strings used as a global default interpreter
  (dynamic-loader prefix) for `[binaries]` entries that do not have their own
  `<name>.interpreter` override.  See the
  [per-binary interpreter](#per-binary-interpreter-posix-only) subsection
  for details.  POSIX-only.

### CMake variables

*New in 0.56.0*

All variables set in the `[cmake]` section will be added to the
generate CMake toolchain file used for both CMake dependencies and
CMake subprojects. The type of each entry must be either a string or a
list of strings.

**Note:** All occurrences of `\` in the value of all keys will be replaced with
          a `/` since CMake has a lot of issues with correctly escaping `\` when
          dealing with variables (even in cases where a path in `CMAKE_C_COMPILER`
          is correctly escaped, CMake will still trip up internally for instance)

          A custom toolchain file should be used (via the `cmake_toolchain_file`
          property) if `\` support is required.

```ini
[cmake]

CMAKE_C_COMPILER    = '/usr/bin/gcc'
CMAKE_CXX_COMPILER  = 'C:\\usr\\bin\\g++'
CMAKE_SOME_VARIABLE = ['some', 'value with spaces']
```

For instance, the `[cmake]` section from above will generate the
following code in the CMake toolchain file:

```cmake
set(CMAKE_C_COMPILER    "/usr/bin/gcc")
set(CMAKE_CXX_COMPILER  "C:/usr/bin/g++")
set(CMAKE_SOME_VARIABLE "some" "value with spaces")
```

### Project specific options

*New in 0.56.0*

Path options are not allowed, those must be set in the `[paths]`
section.

Being able to set project specific options in a cross or native file
can be done using the `[project options]` section of the specific file
(if doing a cross build the options from the native file will be
ignored)

For setting options in subprojects use the `[<subproject>:project
options]` section instead.

```ini
[project options]
build-tests = true

[zlib:project options]
build-tests = false
```

### Meson built-in options

*Before 0.56.0, `<lang>_args` and `<lang>_link_args` must be put in the `properties` section instead, else they will be ignored.*

Meson built-in options can be set the same way:

```ini
[built-in options]
c_std = 'c99'
```

You can set some Meson built-in options on a per-subproject basis,
such as `default_library` and `werror`. The order of precedence is:

1) Command line
2) Machine file
3) Build system definitions

```ini
[zlib:built-in options]
default_library = 'static'
werror = false
```

Options set on a per-subproject basis will inherit the option from the
parent if the parent has a setting but the subproject doesn't, even
when there is a default set Meson language.

```ini
[built-in options]
default_library = 'static'
```

will make subprojects use default_library as static.

Some options can be set on a per-machine basis (in other words, the
value of the build machine can be different than the host machine in a
cross compile). In these cases the values from both a cross file and a
native file are used.

An incomplete list of options is:
- pkg_config_path
- cmake_prefix_path

## Loading multiple machine files

Native files allow layering (cross files can be layered since Meson
0.52.0). More than one file can be loaded, with values from a previous
file being overridden by the next. The intention of this is not
overriding, but to allow composing files. This composition is done by
passing the command line argument multiple times:

```console
meson setup builddir/ --cross-file first.ini --cross-file second.ini --cross-file third.ini
```

In this case `first.ini` will be loaded, then `second.ini`, with
values from `second.ini` replacing `first.ini`, and so on.

For example, if there is a project using C and C++, python 3.4-3.7,
and LLVM 5-7, and it needs to build with clang 5, 6, and 7, and gcc
5.x, 6.x, and 7.x; expressing all of these configurations in
monolithic configurations would result in 81 different native files.
By layering them, it can be expressed by just 12 native files.
