# Reference tables

## Compiler ids

These are return values of the `get_id` method in a compiler object.

| Value     | Compiler family                |
| -----     | ----------------               |
| gcc       | The GNU Compiler Collection    |
| clang     | The Clang compiler             |
| msvc      | Microsoft Visual Studio        |
| intel     | Intel compiler                 |
| llvm      | LLVM-based compiler (Swift, D) |
| mono      | Xamarin C# compiler            |
| dmd       | D lang reference compiler      |
| rustc     | Rust compiler                  |
| valac     | Vala compiler                  |
| pathscale | The Pathscale Fortran compiler |
| pgi       | The Portland Fortran compiler  |
| sun       | Sun Fortran compiler           |
| g95       | The G95 Fortran compiler       |
| open64    | The Open64 Fortran Compiler    |
| nagfor    | The NAG Fortran compiler       |

## Script environment variables

| Value               | Comment                         |
| -----               | -------                         |
| MESON_SOURCE_ROOT   | Absolute path to the source dir |
| MESON_BUILD_ROOT    | Absolute path to the build dir  |
| MESONINTROSPECT     | Command to run to run the introspection command, may be of the form `python /path/to/meson introspect`, user is responsible for splitting the path if necessary. |
| MESON_SUBDIR        | Current subdirectory, only set for `run_command` |

## CPU families

These are returned by the `cpu_family` method of `build_machine`,
`host_machine` and `target_machine`. For cross compilation they are
set in the cross file.

| Value               | Comment                         |
| -----               | -------                         |
| x86                 | 32 bit x86 processor  |
| x86_64              | 64 bit x86 processor  |
| arm                 | 32 bit ARM processor |

Any cpu family not listed in the above list is not guaranteed to
remain stable in future releases.

## Operating system names

These are provided by the `.system()` method call.

| Value               | Comment                         |
| -----               | -------                         |
| linux               | |
| darwin              | Either OSX or iOS |
| windows             | Any version of Windows |
| cygwin              | The Cygwin environment for Windows |
| haiku               | |
| freebsd             | FreeBSD and it's derivatives |
| dragonfly           | DragonFly BSD |
| netbsd              | |

Any string not listed above is not guaranteed to remain stable in
future releases.
