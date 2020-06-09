# Command-line commands

There are two different ways of invoking Meson. First, you can run it directly
from the source tree with the command `/path/to/source/meson.py`. Meson may
also be installed in which case the command is simply `meson`. In this manual
we only use the latter format for simplicity.

Meson is invoked using the following syntax:
`meson [COMMAND] [COMMAND_OPTIONS]`

This section describes all available commands and some of their Optional arguments.
The most common workflow is to run [`setup`](#setup), followed by [`compile`](#compile), and then [`install`](#install).

For the full list of all available options for a specific command use the following syntax:
`meson COMMAND --help`

### configure

```
$ meson configure [-h] [--prefix PREFIX] [--bindir BINDIR]
                  [--datadir DATADIR] [--includedir INCLUDEDIR]
                  [--infodir INFODIR] [--libdir LIBDIR]
                  [--libexecdir LIBEXECDIR] [--localedir LOCALEDIR]
                  [--localstatedir LOCALSTATEDIR] [--mandir MANDIR]
                  [--sbindir SBINDIR] [--sharedstatedir SHAREDSTATEDIR]
                  [--sysconfdir SYSCONFDIR]
                  [--auto-features {enabled,disabled,auto}]
                  [--backend {ninja,vs,vs2010,vs2015,vs2017,vs2019,xcode}]
                  [--buildtype {plain,debug,debugoptimized,release,minsize,custom}]
                  [--debug] [--default-library {shared,static,both}]
                  [--errorlogs] [--install-umask INSTALL_UMASK]
                  [--layout {mirror,flat}] [--optimization {0,g,1,2,3,s}]
                  [--stdsplit] [--strip] [--unity {on,off,subprojects}]
                  [--unity-size UNITY_SIZE] [--warnlevel {0,1,2,3}]
                  [--werror]
                  [--wrap-mode {default,nofallback,nodownload,forcefallback}]
                  [--pkg-config-path PKG_CONFIG_PATH]
                  [--build.pkg-config-path BUILD.PKG_CONFIG_PATH]
                  [--cmake-prefix-path CMAKE_PREFIX_PATH]
                  [--build.cmake-prefix-path BUILD.CMAKE_PREFIX_PATH]
                  [-D option] [--clearcache]
                  [builddir]
```

Reconfigures existing meson project.

Examples:
- `meson configure builddir`: list all available options.
- `meson configure builddir -Doption=new_value`: change a single option

```
positional arguments:
  builddir

optional arguments:
  -h, --help                            show this help message and exit
  --prefix PREFIX                       Installation prefix (default: c:/).
  --bindir BINDIR                       Executable directory (default: bin).
  --datadir DATADIR                     Data file directory (default: share).
  --includedir INCLUDEDIR               Header file directory (default:
                                        include).
  --infodir INFODIR                     Info page directory (default:
                                        share/info).
  --libdir LIBDIR                       Library directory (default: lib).
  --libexecdir LIBEXECDIR               Library executable directory (default:
                                        libexec).
  --localedir LOCALEDIR                 Locale data directory (default:
                                        share/locale).
  --localstatedir LOCALSTATEDIR         Localstate data directory (default:
                                        var).
  --mandir MANDIR                       Manual page directory (default:
                                        share/man).
  --sbindir SBINDIR                     System executable directory (default:
                                        sbin).
  --sharedstatedir SHAREDSTATEDIR       Architecture-independent data directory
                                        (default: com).
  --sysconfdir SYSCONFDIR               Sysconf data directory (default: etc).
  --auto-features {enabled,disabled,auto}
                                        Override value of all 'auto' features
                                        (default: auto).
  --backend {ninja,vs,vs2010,vs2015,vs2017,vs2019,xcode}
                                        Backend to use (default: ninja).
  --buildtype {plain,debug,debugoptimized,release,minsize,custom}
                                        Build type to use (default: debug).
  --debug                               Debug
  --default-library {shared,static,both}
                                        Default library type (default: shared).
  --errorlogs                           Whether to print the logs from failing
                                        tests
  --install-umask INSTALL_UMASK         Default umask to apply on permissions of
                                        installed files (default: 022).
  --layout {mirror,flat}                Build directory layout (default:
                                        mirror).
  --optimization {0,g,1,2,3,s}          Optimization level (default: 0).
  --stdsplit                            Split stdout and stderr in test logs
  --strip                               Strip targets on install
  --unity {on,off,subprojects}          Unity build (default: off).
  --unity-size UNITY_SIZE               Unity block size (default: (2, None,
                                        4)).
  --warnlevel {0,1,2,3}                 Compiler warning level to use (default:
                                        1).
  --werror                              Treat warnings as errors
  --wrap-mode {default,nofallback,nodownload,forcefallback}
                                        Wrap mode (default: default).
  --pkg-config-path PKG_CONFIG_PATH     List of additional paths for pkg-config
                                        to search (default: []). (just for host
                                        machine)
  --build.pkg-config-path BUILD.PKG_CONFIG_PATH
                                        List of additional paths for pkg-config
                                        to search (default: []). (just for build
                                        machine)
  --cmake-prefix-path CMAKE_PREFIX_PATH
                                        List of additional prefixes for cmake to
                                        search (default: []). (just for host
                                        machine)
  --build.cmake-prefix-path BUILD.CMAKE_PREFIX_PATH
                                        List of additional prefixes for cmake to
                                        search (default: []). (just for build
                                        machine)
  -D option                             Set the value of an option, can be used
                                        several times to set multiple options.
  --clearcache                          Clear cached state (e.g. found
                                        dependencies)
```

Most arguments are the same as in [`setup`](#setup).

Note: reconfiguring project will not reset options to their default values (even if they were changed in `meson.build`).

### compile

*(since 0.54.0)*

```
$ meson compile [-h] [-j JOBS] [-l LOAD_AVERAGE] [--clean] [-C BUILDDIR]
```

Builds a default or specified target of a configured meson project.

Example: `meson compile -C builddir`

```
optional arguments:
  -h, --help                            show this help message and exit
  -j JOBS, --jobs JOBS                  The number of worker jobs to run (if
                                        supported). If the value is less than 1
                                        the build program will guess.
  -l LOAD_AVERAGE, --load-average LOAD_AVERAGE
                                        The system load average to try to
                                        maintain (if supported)
  --clean                               Clean the build directory.
  -C BUILDDIR                           The directory containing build files to
                                        be built.
```

### dist

*(since 0.52.0)*

```
$ meson dist [-h] [-C WD] [--formats FORMATS] [--include-subprojects]
             [--no-tests]
```

Generates a release archive from the current source tree.

Example: `meson dist -C builddir`

```
optional arguments:
  -h, --help             show this help message and exit
  -C WD                  directory to cd into before running
  --formats FORMATS      Comma separated list of archive types to create.
  --include-subprojects  Include source code of subprojects that have been used
                         for the build.
  --no-tests             Do not build and test generated packages.
```

This creates a file called `projectname-version.tar.xz` in the build
tree subdirectory `meson-dist`. This archive contains the full
contents of the latest commit in revision control including all the
submodules (recursively). All revision control metadata is removed.
Meson then takes
this archive and tests that it works by doing a full compile + test +
install cycle. If all these pass, Meson will then create a SHA-256
checksum file next to the archive.

**Note**: Meson behaviour is different from Autotools. The Autotools
"dist" target packages up the current source tree. Meson packages
the latest revision control commit. The reason for this is that it
prevents developers from doing accidental releases where the
distributed archive does not match any commit in revision control
(especially the one tagged for the release).

### init

*(since 0.45.0)*

```
$ meson init [-h] [-C WD] [-n NAME] [-e EXECUTABLE] [-d DEPS]
             [-l {c,cpp,cs,cuda,d,fortran,java,objc,objcpp,rust}] [-b]
             [--builddir BUILDDIR] [-f] [--type {executable,library}]
             [--version VERSION]
             [sourcefile [sourcefile ...]]
```

Creates a basic set of build files based on a template.

Example: `meson init -C sourcedir`

```
positional arguments:
  sourcefile                            source files. default: all recognized
                                        files in current directory

optional arguments:
  -h, --help                            show this help message and exit
  -C WD                                 directory to cd into before running
  -n NAME, --name NAME                  project name. default: name of current
                                        directory
  -e EXECUTABLE, --executable EXECUTABLE
                                        executable name. default: project name
  -d DEPS, --deps DEPS                  dependencies, comma-separated
  -l {c,cpp,cs,cuda,d,fortran,java,objc,objcpp,rust}, --language {c,cpp,cs,cuda,d,fortran,java,objc,objcpp,rust}
                                        project language. default: autodetected
                                        based on source files
  -b, --build                           build after generation
  --builddir BUILDDIR                   directory for build
  -f, --force                           force overwrite of existing files and
                                        directories.
  --type {executable,library}           project type. default: executable based
                                        project
  --version VERSION                     project version. default: 0.1
```

### introspect

```
$ meson introspect [-h] [--ast] [--benchmarks] [--buildoptions]
                   [--buildsystem-files] [--dependencies]
                   [--scan-dependencies] [--installed] [--projectinfo]
                   [--targets] [--tests]
                   [--backend {ninja,vs,vs2010,vs2015,vs2017,vs2019,xcode}]
                   [-a] [-i] [-f]
                   [builddir]
```

Displays information about a configured meson project.

Example: `meson introspect builddir`

```
positional arguments:
  builddir                              The build directory

optional arguments:
  -h, --help                            show this help message and exit
  --ast                                 Dump the AST of the meson file.
  --benchmarks                          List all benchmarks.
  --buildoptions                        List all build options.
  --buildsystem-files                   List files that make up the build
                                        system.
  --dependencies                        List external dependencies.
  --scan-dependencies                   Scan for dependencies used in the
                                        meson.build file.
  --installed                           List all installed files and
                                        directories.
  --projectinfo                         Information about projects.
  --targets                             List top level targets.
  --tests                               List all unit tests.
  --backend {ninja,vs,vs2010,vs2015,vs2017,vs2019,xcode}
                                        The backend to use for the
                                        --buildoptions introspection.
  -a, --all                             Print all available information.
  -i, --indent                          Enable pretty printed JSON.
  -f, --force-object-output             Always use the new JSON format for
                                        multiple entries (even for 0 and 1
                                        introspection commands)
```

### install

*(since 0.47.0)*

```
$ meson install [-h] [-C WD] [--no-rebuild] [--only-changed] [--quiet]
```

Installs the project to the prefix specified in `setup`.

Examples: 
- `meson install -C builddir`.
- `DESTDIR=/path/to/staging/area meson install -C builddir`

```
optional arguments:
  -h, --help      show this help message and exit
  -C WD           directory to cd into before running
  --no-rebuild    Do not rebuild before installing.
  --only-changed  Only overwrite files that are older than the copied file.
  --quiet         Do not print every file that was installed.
```

See [the installation documentation](Installing.md) for more info.

### rewrite

*(since 0.50.0)*

```
$ meson rewrite [-h] [-s SRCDIR] [-V] [-S]
                {target,kwargs,default-options,command} ...
```

Modifies the meson project.

```
optional arguments:
  -h, --help                            show this help message and exit
  -s SRCDIR, --sourcedir SRCDIR         Path to source directory.
  -V, --verbose                         Enable verbose output
  -S, --skip-errors                     Skip errors instead of aborting

Rewriter commands:
  Rewrite command to execute

  {target,kwargs,default-options,command}
    target                              Modify a target
    kwargs                              Modify keyword arguments
    default-options                     Modify the project default options
    command                             Execute a JSON array of commands
```

See [the meson file rewriter documentation](Rewriter.md) for more info.

### setup

```
$ meson setup [-h] [--prefix PREFIX] [--bindir BINDIR] [--datadir DATADIR]
              [--includedir INCLUDEDIR] [--infodir INFODIR]
              [--libdir LIBDIR] [--libexecdir LIBEXECDIR]
              [--localedir LOCALEDIR] [--localstatedir LOCALSTATEDIR]
              [--mandir MANDIR] [--sbindir SBINDIR]
              [--sharedstatedir SHAREDSTATEDIR] [--sysconfdir SYSCONFDIR]
              [--auto-features {enabled,disabled,auto}]
              [--backend {ninja,vs,vs2010,vs2015,vs2017,vs2019,xcode}]
              [--buildtype {plain,debug,debugoptimized,release,minsize,custom}]
              [--debug] [--default-library {shared,static,both}]
              [--errorlogs] [--install-umask INSTALL_UMASK]
              [--layout {mirror,flat}] [--optimization {0,g,1,2,3,s}]
              [--stdsplit] [--strip] [--unity {on,off,subprojects}]
              [--unity-size UNITY_SIZE] [--warnlevel {0,1,2,3}] [--werror]
              [--wrap-mode {default,nofallback,nodownload,forcefallback}]
              [--pkg-config-path PKG_CONFIG_PATH]
              [--build.pkg-config-path BUILD.PKG_CONFIG_PATH]
              [--cmake-prefix-path CMAKE_PREFIX_PATH]
              [--build.cmake-prefix-path BUILD.CMAKE_PREFIX_PATH]
              [-D option] [--native-file NATIVE_FILE]
              [--cross-file CROSS_FILE] [-v] [--fatal-meson-warnings]
              [--reconfigure] [--wipe]
              [builddir] [sourcedir]
```

The default meson command (invoked if there was no COMMAND supplied).

Configures a build directory for the meson project.

Example: `meson setup builddir`

```
positional arguments:
  builddir
  sourcedir

optional arguments:
  -h, --help                            show this help message and exit
  --prefix PREFIX                       Installation prefix (default: c:/).
  --bindir BINDIR                       Executable directory (default: bin).
  --datadir DATADIR                     Data file directory (default: share).
  --includedir INCLUDEDIR               Header file directory (default:
                                        include).
  --infodir INFODIR                     Info page directory (default:
                                        share/info).
  --libdir LIBDIR                       Library directory (default: lib).
  --libexecdir LIBEXECDIR               Library executable directory (default:
                                        libexec).
  --localedir LOCALEDIR                 Locale data directory (default:
                                        share/locale).
  --localstatedir LOCALSTATEDIR         Localstate data directory (default:
                                        var).
  --mandir MANDIR                       Manual page directory (default:
                                        share/man).
  --sbindir SBINDIR                     System executable directory (default:
                                        sbin).
  --sharedstatedir SHAREDSTATEDIR       Architecture-independent data directory
                                        (default: com).
  --sysconfdir SYSCONFDIR               Sysconf data directory (default: etc).
  --auto-features {enabled,disabled,auto}
                                        Override value of all 'auto' features
                                        (default: auto).
  --backend {ninja,vs,vs2010,vs2015,vs2017,vs2019,xcode}
                                        Backend to use (default: ninja).
  --buildtype {plain,debug,debugoptimized,release,minsize,custom}
                                        Build type to use (default: debug).
  --debug                               Debug
  --default-library {shared,static,both}
                                        Default library type (default: shared).
  --errorlogs                           Whether to print the logs from failing
                                        tests
  --install-umask INSTALL_UMASK         Default umask to apply on permissions of
                                        installed files (default: 022).
  --layout {mirror,flat}                Build directory layout (default:
                                        mirror).
  --optimization {0,g,1,2,3,s}          Optimization level (default: 0).
  --stdsplit                            Split stdout and stderr in test logs
  --strip                               Strip targets on install
  --unity {on,off,subprojects}          Unity build (default: off).
  --unity-size UNITY_SIZE               Unity block size (default: (2, None,
                                        4)).
  --warnlevel {0,1,2,3}                 Compiler warning level to use (default:
                                        1).
  --werror                              Treat warnings as errors
  --wrap-mode {default,nofallback,nodownload,forcefallback}
                                        Wrap mode (default: default).
  --pkg-config-path PKG_CONFIG_PATH     List of additional paths for pkg-config
                                        to search (default: []). (just for host
                                        machine)
  --build.pkg-config-path BUILD.PKG_CONFIG_PATH
                                        List of additional paths for pkg-config
                                        to search (default: []). (just for build
                                        machine)
  --cmake-prefix-path CMAKE_PREFIX_PATH
                                        List of additional prefixes for cmake to
                                        search (default: []). (just for host
                                        machine)
  --build.cmake-prefix-path BUILD.CMAKE_PREFIX_PATH
                                        List of additional prefixes for cmake to
                                        search (default: []). (just for build
                                        machine)
  -D option                             Set the value of an option, can be used
                                        several times to set multiple options.
  --native-file NATIVE_FILE             File containing overrides for native
                                        compilation environment.
  --cross-file CROSS_FILE               File describing cross compilation
                                        environment.
  -v, --version                         show program's version number and exit
  --fatal-meson-warnings                Make all Meson warnings fatal
  --reconfigure                         Set options and reconfigure the project.
                                        Useful when new options have been added
                                        to the project and the default value is
                                        not working.
  --wipe                                Wipe build directory and reconfigure
                                        using previous command line options.
                                        Useful when build directory got
                                        corrupted, or when rebuilding with a
                                        newer version of meson.
```

See [meson introduction page](Running-Meson.md#configuring-the-build-directory) for more info.

### subprojects

*(since 0.49.0)*

```
$ meson subprojects [-h] {update,checkout,download,foreach} ...
```

Manages subprojects of the meson project.

```
optional arguments:
  -h, --help                          show this help message and exit

Commands:
  {update,checkout,download,foreach}
    update                            Update all subprojects from wrap files
    checkout                          Checkout a branch (git only)
    download                          Ensure subprojects are fetched, even if
                                      not in use. Already downloaded subprojects
                                      are not modified. This can be used to pre-
                                      fetch all subprojects and avoid downloads
                                      during configure.
    foreach                           Execute a command in each subproject
                                      directory.
```

### test

```
$ meson test [-h] [--repeat REPEAT] [--no-rebuild] [--gdb]
             [--gdb-path GDB_PATH] [--list] [--wrapper WRAPPER] [-C WD]
             [--suite SUITE] [--no-suite SUITE] [--no-stdsplit]
             [--print-errorlogs] [--benchmark] [--logbase LOGBASE]
             [--num-processes NUM_PROCESSES] [-v] [-q]
             [-t TIMEOUT_MULTIPLIER] [--setup SETUP]
             [--test-args TEST_ARGS]
             [args [args ...]]
```

Run tests for the configure meson project.

Example: `meson test -C builddir`

```
positional arguments:
  args                                  Optional list of tests to run

optional arguments:
  -h, --help                            show this help message and exit
  --repeat REPEAT                       Number of times to run the tests.
  --no-rebuild                          Do not rebuild before running tests.
  --gdb                                 Run test under gdb.
  --gdb-path GDB_PATH                   Path to the gdb binary (default: gdb).
  --list                                List available tests.
  --wrapper WRAPPER                     wrapper to run tests with (e.g.
                                        Valgrind)
  -C WD                                 directory to cd into before running
  --suite SUITE                         Only run tests belonging to the given
                                        suite.
  --no-suite SUITE                      Do not run tests belonging to the given
                                        suite.
  --no-stdsplit                         Do not split stderr and stdout in test
                                        logs.
  --print-errorlogs                     Whether to print failing tests' logs.
  --benchmark                           Run benchmarks instead of tests.
  --logbase LOGBASE                     Base name for log file.
  --num-processes NUM_PROCESSES         How many parallel processes to use.
  -v, --verbose                         Do not redirect stdout and stderr
  -q, --quiet                           Produce less output to the terminal.
  -t TIMEOUT_MULTIPLIER, --timeout-multiplier TIMEOUT_MULTIPLIER
                                        Define a multiplier for test timeout,
                                        for example when running tests in
                                        particular conditions they might take
                                        more time to execute.
  --setup SETUP                         Which test setup to use.
  --test-args TEST_ARGS                 Arguments to pass to the specified
                                        test(s) or all tests
```

See [the unit test documentation](Unit-tests.md) for more info.

### wrap

```
$ meson wrap [-h] {list,search,install,update,info,status,promote} ...
```

An utility to manage WrapDB dependencies.

```
optional arguments:
  -h, --help                            show this help message and exit

Commands:
  {list,search,install,update,info,status,promote}
    list                                show all available projects
    search                              search the db by name
    install                             install the specified project
    update                              update the project to its newest
                                        available release
    info                                show available versions of a project
    status                              show installed and available versions of
                                        your projects
    promote                             bring a subsubproject up to the master
                                        project
```

See [the WrapDB tool documentation](Using-wraptool.md) for more info.
