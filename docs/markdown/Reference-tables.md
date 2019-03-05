# Reference tables

## Compiler ids

These are return values of the `get_id` (Compiler family) and
`get_argument_syntax` (Argument syntax) method in a compiler object.

| Value     | Compiler family                  | Argument syntax                |
| -----     | ---------------                  | ---------------                |
| arm       | ARM compiler                     |                                |
| armclang  | ARMCLANG compiler                |                                |
| ccrx      | Renesas RX Family C/C++ compiler |                                |
| clang     | The Clang compiler               | gcc                            |
| clang-cl  | The Clang compiler (MSVC compatible driver) | msvc                |
| dmd       | D lang reference compiler        |                                |
| flang     | Flang Fortran compiler           |                                |
| g95       | The G95 Fortran compiler         |                                |
| gcc       | The GNU Compiler Collection      | gcc                            |
| intel     | Intel compiler                   | msvc on windows, otherwise gcc |
| lcc       | Elbrus C/C++/Fortran Compiler    |                                |
| llvm      | LLVM-based compiler (Swift, D)   |                                |
| mono      | Xamarin C# compiler              |                                |
| msvc      | Microsoft Visual Studio          | msvc                           |
| nagfor    | The NAG Fortran compiler         |                                |
| open64    | The Open64 Fortran Compiler      |                                |
| pathscale | The Pathscale Fortran compiler   |                                |
| pgi       |  Portland PGI C/C++/Fortran compilers |                                |
| rustc     | Rust compiler                    |                                |
| sun       | Sun Fortran compiler             |                                |
| valac     | Vala compiler                    |                                |

## Script environment variables

| Value               | Comment                         |
| -----               | -------                         |
| MESONINTROSPECT     | Command to run to run the introspection command, may be of the form `python /path/to/meson introspect`, user is responsible for splitting the path if necessary. |
| MESON_BUILD_ROOT    | Absolute path to the build dir  |
| MESON_DIST_ROOT     | Points to the root of the staging directory, only set when running `dist` scripts |
| MESON_SOURCE_ROOT   | Absolute path to the source dir |
| MESON_SUBDIR        | Current subdirectory, only set for `run_command` |


## CPU families

These are returned by the `cpu_family` method of `build_machine`,
`host_machine` and `target_machine`. For cross compilation they are
set in the cross file.

| Value               | Comment                         |
| -----               | -------                         |
| aarch64             | 64 bit ARM processor  |
| arc                 | 32 bit ARC processor  |
| arm                 | 32 bit ARM processor  |
| e2k                 | MCST Elbrus processor |
| ia64                | Itanium processor     |
| mips                | 32 bit MIPS processor |
| mips64              | 64 bit MIPS processor |
| parisc              | HP PA-RISC processor  |
| ppc                 | 32 bit PPC processors |
| ppc64               | 64 bit PPC processors |
| riscv32             | 32 bit RISC-V Open ISA|
| riscv64             | 64 bit RISC-V Open ISA|
| rl78                | Renesas RL78          |
| rx                  | Renesas RX 32 bit MCU |
| s390x               | IBM zSystem s390x     |
| sparc               | 32 bit SPARC          |
| sparc64             | SPARC v9 processor    |
| x86                 | 32 bit x86 processor  |
| x86_64              | 64 bit x86 processor  |

Any cpu family not listed in the above list is not guaranteed to
remain stable in future releases.

Those porting from autotools should note that meson does not add
endianness to the name of the cpu_family. For example, autotools
will call little endian PPC64 "ppc64le", meson will not, you must
also check the `.endian()` value of the machine for this information.

## Operating system names

These are provided by the `.system()` method call.

| Value               | Comment                         |
| -----               | -------                         |
| cygwin              | The Cygwin environment for Windows |
| darwin              | Either OSX or iOS |
| dragonfly           | DragonFly BSD |
| freebsd             | FreeBSD and its derivatives |
| gnu                 | GNU Hurd |
| haiku               | |
| linux               | |
| netbsd              | |
| windows             | Any version of Windows |

Any string not listed above is not guaranteed to remain stable in
future releases.


## Language arguments parameter names

These are the parameter names for passing language specific arguments to your build target.

| Language      | compiler name | linker name       |
| ------------- | ------------- | ----------------- |
| C             | c_args        | c_link_args       |
| C++           | cpp_args      | cpp_link_args     |
| C#            | cs_args       | cs_link_args      |
| D             | d_args        | d_link_args       |
| Fortran       | fortran_args  | fortran_link_args |
| Java          | java_args     | java_link_args    |
| Objective C   | objc_args     | objc_link_args    |
| Objective C++ | objcpp_args   | objcpp_link_args  |
| Rust          | rust_args     | rust_link_args    |
| Vala          | vala_args     | vala_link_args    |

## Compiler and linker flag environment variables

These environment variables will be used to modify the compiler and
linker flags.

It is recommended that you **do not use these**. They are provided purely to
for backwards compatibility with other build systems. There are many caveats to
their use, especially when rebuilding the project. It is **highly** recommended
that you use [the command line arguments](#language-arguments-parameters-names)
instead.

| Name      | Comment                                  |
| -----     | -------                                  |
| CFLAGS    | Flags for the C compiler                 |
| CXXFLAGS  | Flags for the C++ compiler               |
| OBJCFLAGS | Flags for the Objective C compiler       |
| FFLAGS    | Flags for the Fortran compiler           |
| DFLAGS    | Flags for the D compiler                 |
| VALAFLAGS | Flags for the Vala compiler              |
| RUSTFLAGS | Flags for the Rust compiler              |
| LDFLAGS   | The linker flags, used for all languages |

## Function Attributes

These are the parameters names that are supported using
`compiler.has_function_attribute()` or
`compiler.get_supported_function_attributes()`

### GCC `__attribute__`

These values are supported using the GCC style `__attribute__` annotations,
which are supported by GCC, Clang, and other compilers.


| Name                 |
|----------------------|
| alias                |
| aligned              |
| alloc_size           |
| always_inline        |
| artificial           |
| cold                 |
| const                |
| constructor          |
| constructor_priority |
| deprecated           |
| destructor           |
| error                |
| externally_visible   |
| fallthrough          |
| flatten              |
| format               |
| format_arg           |
| gnu_inline           |
| hot                  |
| ifunc                |
| malloc               |
| noclone              |
| noinline             |
| nonnull              |
| noreturn             |
| nothrow              |
| optimize             |
| packed               |
| pure                 |
| returns_nonnull      |
| unused               |
| used                 |
| visibility           |
| warning              |
| warn_unused_result   |
| weak                 |
| weakreaf             |

### MSVC __declspec

These values are supported using the MSVC style `__declspec` annotation,
which are supported by MSVC, GCC, Clang, and other compilers.

| Name                 |
|----------------------|
| dllexport            |
| dllimport            |


## Dependency lookup methods

These are the values that can be passed to `dependency` function's
`method` keyword argument.

| Name              | Comment                                      |
| -----             | -------                                      |
| auto              | Automatic method selection                   |
| pkg-config        | Use Pkg-Config                               |
| cmake             | Look up as a CMake module                    |
| config-tool       | Use a custom dep tool such as `cups-config`  |
| system            | System provided (e.g. OpenGL)                |
| extraframework    | A macOS/iOS framework                        |
