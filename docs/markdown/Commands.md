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

Reconfigures existing meson project.

Examples:
- `meson configure builddir`: list all available options.
- `meson configure builddir -Doption=new_value`: change a single option

Positional arguments:
- `builddir`: path to the configured build directory

Optional arguments:
- `--prefix PREFIX`: Installation prefix.
- `--bindir BINDIR`: Executable directory.
- `--datadir DATADIR`: Data file directory.
- `--includedir INCLUDEDIR`: Header file directory.
- `--infodir INFODIR`: Info page directory.
- `--libdir LIBDIR`: Library directory.
- `--libexecdir LIBEXECDIR`: Library executable directory.
- `--localedir LOCALEDIR`: Locale data directory.
- `--localstatedir LOCALSTATEDIR`: Localstate data directory.
- `--mandir MANDIR`: Manual page directory.
- `--sbindir SBINDIR`: System executable directory.
- `--sharedstatedir SHAREDSTATEDIR`: Architecture-independent data directory.
- `--sysconfdir SYSCONFDIR`: Sysconf data directory.
- `--auto-features`: Override value of all 'auto' features.
- `--backend`: Backend to use.
- `--buildtype`: Build type to use.
- `--debug`: Debug.
- `--default-library`: Default library type.
- `--errorlogs`: Whether to print the logs from failing tests.
- `--install-umask INSTALL_UMASK`: Default umask to apply on permissions of installed files.
- `--layout`: Build directory layout.
- `--optimization`: Optimization level.
- `--stdsplit`: Split stdout and stderr in test logs.
- `--strip`: Strip targets on install.
- `--unity`: Unity build.
- `--unity-size UNITY_SIZE`: Unity block size.
- `--warnlevel`: Compiler warning level to use.
- `--werror`: Treat warnings as errors.
- `--wrap-mode`: Wrap mode.
- `--pkg-config-path PKG_CONFIG_PATH`: List of additional paths for pkg-config to search (just for host machine).
- `--build.pkg-config-path BUILD.PKG_CONFIG_PATH`: List of additional paths for pkg-config to search (just for build machine).
- `--cmake-prefix-path CMAKE_PREFIX_PATH`: List of additional prefixes for cmake to search (just for host machine).
- `--build.cmake-prefix-path BUILD.CMAKE_PREFIX_PATH`: List of additional prefixes for cmake to search (just for build machine).
- `-D option`: Set the value of an option, can be used several times to set multiple options.
- `--clearcache`: Clear cached state (e.g. found dependencies)

Most arguments are the same as in [`setup`](#setup).

Note: reconfiguring project will not reset options to their default values (even if they were changed in `meson.build`).

### compile

*(since 0.54.0)*

Builds a default or specified target of a configured meson project.

Example: `meson compile -C builddir`

Optional arguments:
- `-j JOBS, --jobs JOBS`: The number of worker jobs to run (if supported). If the value is less than 1 the build program will guess.
- `-l LOAD_AVERAGE, --load-average LOAD_AVERAGE`: The system load average to try to maintain (if supported).
- `--clean`: Clean the build directory.
- `-C BUILDDIR`: The directory containing build files to be built.

### dist

*(since 0.52.0)*

Generates a release archive from the current source tree.

Example: `meson dist -C builddir`

Optional arguments:
- `-C WD`: directory to cd into before running.
- `--formats FORMATS`: Comma separated list of archive types to create.
- `--include-subprojects`: Include source code of subprojects that have been used for the build.
- `--no-tests`: Do not build and test generated packages.

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

Creates a basic set of build files based on a template.

Example: `meson init -C sourcedir`

Positional arguments:
- `sourcefile`: source files. default: all recognized files in current directory.

Optional arguments:
- `-C WD`: directory to cd into before running.
- `-n NAME, --name NAME`: project name. default: name of current directory.
- `-e EXECUTABLE, --executable EXECUTABLE`: executable name. default: project name.
- `-d DEPS, --deps DEPS`: dependencies, comma-separated.
- `-l`: project language. default: autodetected based on source files.
- `-b, --build`: build after generation.
- `--builddir BUILDDIR`: directory for build.
- `-f, --force`: force overwrite of existing files and directories.
- `--type`: project type. default: executable based project.
- `--version VERSION`: project version. default: 0.1

### introspect

Displays information about a configured meson project.

Syntax: `meson introspect [builddir] INTROSPECT_COMMAND [introspect_command_options]`  
Example: `meson introspect builddir`

Positional arguments:
- `builddir`: The build directory

Optional arguments:
- `--ast`: Dump the AST of the meson file.
- `--benchmarks`: List all benchmarks.
- `--buildoptions`: List all build options.
- `--buildsystem-files`: List files that make up the build system.
- `--dependencies`: List external dependencies.
- `--scan-dependencies`: Scan for dependencies used in the meson.build file.
- `--installed`: List all installed files and directories.
- `--projectinfo`: Information about projects.
- `--targets`: List top level targets.
- `--tests`: List all unit tests.
- `--backend`: The backend to use for the --buildoptions introspection.
- `-a, --all`: Print all available information.
- `-i, --indent`: Enable pretty printed JSON.
- `-f, --force-object-output`: Always use the new JSON format for multiple entries (even for 0 and 1 introspection commands)

### install

*(since 0.47.0)*

Installs the project to the prefix specified in `setup`.

Examples: 
- `meson install -C builddir`.
- `DESTDIR=/path/to/staging/area meson install -C builddir`

Optional arguments:
- `-C WD`: directory to cd into before running.
- `--no-rebuild`: Do not rebuild before installing.
- `--only-changed`: Only overwrite files that are older than the copied file.
- `--quiet`: Do not print every file that was installed.

See [the installation documentation](Installing.md) for more info.

### rewrite

*(since 0.50.0)*

Modifies the meson project.

Optional arguments:
- `-s SRCDIR, --sourcedir SRCDIR`: Path to source directory.
- `-V, --verbose`: Enable verbose output.
- `-S, --skip-errors`: Skip errors instead of aborting

Commands:
- `target`: Modify a target.
- `kwargs`: Modify keyword arguments.
- `default-options`: Modify the project default options.
- `command`: Execute a JSON array of commands

See [the meson file rewriter documentation](Rewriter.md) for more info.

### setup

The default meson command (invoked if there was no COMMAND supplied).

Configures a build directory for the meson project.

Example: `meson setup builddir`

Positional arguments:
- `builddir`: path to the build directory.
- `sourcedir`: path to the directory containing the root `meson.build`.

Optional arguments:
- `--prefix PREFIX`: Installation prefix.
- `--bindir BINDIR`: Executable directory.
- `--datadir DATADIR`: Data file directory.
- `--includedir INCLUDEDIR`: Header file directory.
- `--infodir INFODIR`: Info page directory.
- `--libdir LIBDIR`: Library directory.
- `--libexecdir LIBEXECDIR`: Library executable directory.
- `--localedir LOCALEDIR`: Locale data directory.
- `--localstatedir LOCALSTATEDIR`: Localstate data directory.
- `--mandir MANDIR`: Manual page directory.
- `--sbindir SBINDIR`: System executable directory.
- `--sharedstatedir SHAREDSTATEDIR`: Architecture-independent data directory.
- `--sysconfdir SYSCONFDIR`: Sysconf data directory.
- `--auto-features`: Override value of all 'auto' features.
- `--backend`: Backend to use.
- `--buildtype`: Build type to use.
- `--debug`: Debug.
- `--default-library`: Default library type.
- `--errorlogs`: Whether to print the logs from failing tests.
- `--install-umask INSTALL_UMASK`: Default umask to apply on permissions of installed files.
- `--layout`: Build directory layout.
- `--optimization`: Optimization level.
- `--stdsplit`: Split stdout and stderr in test logs.
- `--strip`: Strip targets on install.
- `--unity`: Unity build.
- `--unity-size UNITY_SIZE`: Unity block size.
- `--warnlevel`: Compiler warning level to use.
- `--werror`: Treat warnings as errors.
- `--wrap-mode`: Wrap mode.
- `--pkg-config-path PKG_CONFIG_PATH`: List of additional paths for pkg-config to search (just for host machine).
- `--build.pkg-config-path BUILD.PKG_CONFIG_PATH`: List of additional paths for pkg-config to search (just for build machine).
- `--cmake-prefix-path CMAKE_PREFIX_PATH`: List of additional prefixes for cmake to search (just for host machine).
- `--build.cmake-prefix-path BUILD.CMAKE_PREFIX_PATH`: List of additional prefixes for cmake to search (just for build machine).
- `-D option`: Set the value of an option, can be used several times to set multiple options.
- `--native-file NATIVE_FILE`: File containing overrides for native compilation environment.
- `--cross-file CROSS_FILE`: File describing cross compilation environment.
- `-v, --version`: show program's version number and exit.
- `--fatal-meson-warnings`: Make all Meson warnings fatal.
- `--reconfigure`: Set options and reconfigure the project. Useful when new options have been added to the project and the default value is not working.
- `--wipe`: Wipe build directory and reconfigure using previous command line options. Userful when build directory got corrupted, or when rebuilding with a newer version of meson.

See [meson introduction page](Running-Meson.md#configuring-the-build-directory) for more info.

### subprojects

*(since 0.49.0)*

Manages subprojects of the meson project.

Syntax: `meson subprojects SUBPROJECTS_COMMAND [subprojects_command_options]`

Commands:
- `update`: Update all subprojects from wrap files.
- `checkout`: Checkout a branch (git only).
- `download`: Ensure subprojects are fetched, even if not in use. Already downloaded subprojects are not modified. This can be used to pre-fetch all subprojects and avoid downloads during configure.
- `foreach`: Execute a command in each subproject directory.

### test

Run tests for the configure meson project.

Example: `meson test -C builddir`

Positional arguments:
- `args`: Optional list of tests to run

Optional arguments:
- `--repeat REPEAT`: Number of times to run the tests.
- `--no-rebuild`: Do not rebuild before running tests.
- `--gdb`: Run test under gdb.
- `--gdb-path GDB_PATH`: Path to the gdb binary.
- `--list`: List available tests.
- `--wrapper WRAPPER`: wrapper to run tests with (e.g. Valgrind).
- `-C WD`: directory to cd into before running.
- `--suite SUITE`: Only run tests belonging to the given suite.
- `--no-suite SUITE`: Do not run tests belonging to the given suite.
- `--no-stdsplit`: Do not split stderr and stdout in test logs.
- `--print-errorlogs`: Whether to print failing tests' logs.
- `--benchmark`: Run benchmarks instead of tests.
- `--logbase LOGBASE`: Base name for log file.
- `--num-processes NUM_PROCESSES`: How many parallel processes to use.
- `-v, --verbose`: Do not redirect stdout and stderr.
- `-q, --quiet`: Produce less output to the terminal.
- `-t TIMEOUT_MULTIPLIER, --timeout-multiplier TIMEOUT_MULTIPLIER`: Define a multiplier for test timeout, for example when running tests in particular conditions they might take more time to execute.
- `--setup SETUP`: Which test setup to use.
- `--test-args TEST_ARGS`: Arguments to pass to the specified test(s) or all tests

See [the unit test documentation](Unit-tests.md) for more info.

### wrap

An utility to manage WrapDB dependencies.

Commands:
- `list`: show all available projects.
- `search`: search the db by name.
- `install`: install the specified project.
- `update`: update the project to its newest available release.
- `info`: show available versions of a project.
- `status`: show installed and available versions of your projects.
- `promote`: bring a subsubproject up to the master project

See [the WrapDB tool documentation](Using-wraptool.md) for more info.
