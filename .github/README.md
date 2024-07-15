# `hadron` composite build system for C++/JavaScript Node-API modules

This is the core of the `hadron` build system for dual-environment Node.js/Browser C++/JavaScript Node-API modules.

It consists of:
  * This modified `meson` core that includes:
    - A `node-api` module that greatly simplifies building dual-environment (native code in Node.js and WASM in the browser) C and C++ projects
    - Improved `CMake` compatibility with:
        * Support for `conan` `CMake` config files
        * Support for `$CONFIG` generator expressions
        * Support for `install_data(FILES ...)`
        * Several bugfixes related to handling the target dependencies
  * [`xpm`](https://xpack.github.io/xpm/) as build orchestrator and build tools software package manager
  * [`conan`](https://conan.io) as C/C++ package manager
  * [xPacks](https://xpack.github.io/) as standalone build tools packages

It is meant to be the preferred build system for [SWIG JSE](https://github.com/mmomtchev/swig)-generated projects.

# Comparison vs `node-gyp`

| Description | `node-gyp` | `hadron` = `meson` + `conan` + `xpm` |
| --- | --- | --- |
| Overview  | The official Node.js and Node.js native addon build system from the Node.js core team, inherited and adapted from the early days of V8 / Chromium  | A new experimental build system from the SWIG JSE author that follows the `meson` design principles |
| Status | Very mature | Very young project |
| Platforms with native builds | All platforms supported by Node.js  | Linux, Windows and macOS |
| WASM builds | Hackish, see `swig-napi-example-project` and `magickwand.js@1.1` for solutions | Out of the box |
| Node.js APIs | All APIs, including the now obsolete raw V8 and NAN and the current Node-API | Only Node-API |
| Integration with other builds systems for external dependencies | Very hackish, see `magickwand.js@1.1` for solutions, the only good solution is to recreate the build system of all dependencies around `node-gyp` | Out of the box support for `meson`, `CMake` and `autotools` |
| `conan` integration | Very hackish, see `magickwand.js@1.0` | Out of the box |
| Build configurations through `npm install` CLI options | Yes | Yes |
| Distributing prebuilt binaries | Yes, multiple options, including `@mapbox/node-pre-gyp`, `prebuild-install` and `prebuildify` | Only `prebuild-install` at the moment |
| Requirements for the target host when installing from source | Node.js, Python and a working C++17 build environment | Only Node.js  when using `xpack-dev-tools`, a working C++17 build environment otherwise |
| Makefile language | Obscure and obsolete (`gyp`) | Modern and supported (`meson`)

When choosing a build system, if your project:

 * targets only Node.js/native and has no dependencies

    → stay on `node-gyp`

 * meant to be distributed only as binaries compiled in a controlled environment

    → stay on `node-gyp`

 * has a dual-environment native/WASM setup

    → `node-gyp` will work for you, but `hadron` has some advantages

 * has dependencies with different build systems (`meson`, `CMake`, `autotools`)

    → `hadron` is the much better choice

 * uses `conan`

    → `hadron` is the much better choice

 * everything else at once - or must support compilation on all end-users' machines without any assumptions about the installed software

    → `hadron` is the only choice


# Installation

The modified `meson` core is a xPack:

```shell
npm install xpm
npx xpm install @mmomtchev/meson-xpack
```

# Tutorial

* [Project setup](#project-setup)
* [Create `meson.build`](#create-mesonbuild)
* [Setup the build actions](#setup-the-build-actions)
* [Build for the first time](#build-for-the-first-time)
* [Add WASM](#add-wasm)
* [Add async support](#add-async-support)
* [Add a `CMake`-based subproject](#add-a-cmake-based-subproject)
* [Add build options](#add-build-options)
* [Add `conan`](#add-conan)
* [Add prebuilt binaries and `npm install` scripts](#add-prebuilt-binaries-and-npm-install-scripts)
* [Advanced `node-api` options](#advanced-node-api-options)
* [Advanced `xpm`, `meson` and `conan` options](#advanced-xpm-meson-and-conan-options)

The best way to start a new `hadron` project is by cloning the [SWIG Node-API Example Project (`hadron`)](https://github.com/mmomtchev/hadron-swig-napi-example-project.git) - it is a full project template that includes every basic feature and uses SWIG to generate the code.

This tutorial will guide you step by step through all the features, giving you a better understanding of each element.

## Project setup

Write some C/C++ code and use SWIG to generate Node-API compatible bindings or manually write the glue code yourself - this part is beyond the scope of this tutorial.

Initialize a new `npm` project, install `xpm` and initialize the `xpm` extension:

```shell
npm init
npm install xpm
npx xpm init
```

If using C++, install `node-addon-api`:

*(omit all `--save-dev` if you plan to be able to build on the end-user's machine when installing)*
```shell
npm install --save-dev node-addon-api
```

Install the `meson` and `ninja` xPacks:

```shell
xpm install @mmomtchev/meson-xpack @xpack-dev-tools/ninja-build
```

## Create `meson.build`

```python
project(
  'My Project',
  ['cpp'],
  default_options: [
    # Not mandatory, but this is the default when using node-gyp
    # (in meson, the default is buildtype=debug)
    'buildtype=release',
    # Highly recommended if you are shipping binaries for Windows
    # and want to avoid your users the Windows DLL hell and random crashes
    'b_vscrt=static_from_buildtype'
  ]
)

# Simply include the module, this step will also parse all
# npm_config_ options into meson options
napi = import('node-api')

# Use napi.extension_module() instead of
# shared_module() with the same arguments
addon = napi.extension_module(
  # The name of the addon
  'my_addon',
  # The sources
  [ 'src/my_source.cc' ]
)
```

## Setup the build actions

Add to `package.json` which should already have an empty `xpack.actions` element:

```json
{
  ...
  "xpack": {
    "actions": {
      "prepare": "meson setup build .",
      "build": "meson compile -C build -v"
    }
  }
  ...
}
```

## Build for the first time

```shell
npx xpm run prepare
npx xpm run build
```

Your new addon should be waiting for you in `build/my_addon.node`.

## Add WASM

In order to build to WASM, `emscripten` must be installed and activated in the environment.

Create a `meson` cross-file, the bare minimum is:

```ini
[binaries]
c = 'emcc'
cpp = 'em++'
ar = 'emar'
strip = 'emstrip'

[host_machine]
system = 'emscripten'
cpu_family = 'wasm32'
cpu = 'wasm32'
endian = 'little'
```

Then, the project `package.json` will have to be modified to include build configurations:

```json
{
  ...
  "actions": {
    "build": "meson compile -C build -v"
  },
  "buildConfigurations": {
    "native": {
      "actions": {
        "prepare": "meson setup build ."
      }
    },
    "wasm": {
      "actions": {
        "prepare": "meson setup build . --cross-file emscripten-wasm32.ini"
      }
    }
  }
  ...
}
```

The `build` step is common to both configurations, but from now on, when calling `prepare`, the configuration will have to be specified:

```shell
npx xpm run prepare --config wasm
npx xpm run build
```

Finally, install `emnapi`, add `c` as language in `project()` in `meson.build`, and launch your first WASM build:

*(omit all `--save-dev` if you plan to be able to build on the end-user's machine when installing)*

```shell
npm install --save-dev emnapi
npm install @emnapi/runtime
```

## Add async support

If building to WASM with async support, multi-threading must be explicitly enabled:
```python
thread_dep = dependency('threads')
addon = napi.extension_module(
  'my_addon',
  [ 'src/my_source.cc' ],
  dependencies: [ thread_dep ]
  )
```

In this case the resulting WASM will require [`COOP`/`COEP`](https://web.dev/articles/coop-coep) when loaded in a browser.

Node.js always has async support and including the `thread` dependency is a no-op when building to native.

## Add a `CMake`-based subproject

`meson` has native support for `CMake`-based subprojects through its `cmake` module:

```python
cmake = import('cmake')
cmake_opts = cmake.subproject_options()
cmake_opts.add_cmake_defines([
  # You can pass your CMake options here, CMAKE_BUILD_TYPE is automatic
  # from the meson build type
  {'BUILD_SHARED_LIBS': false},
  {'BUILD_UTILITIES': not meson.is_cross_build()},
  # Always pass this for a Node.js addon
  {'CMAKE_POSITION_INDEPENDENT_CODE': true}
])
# This will retrieve the CMakeLibrary::CMakeTarget target
my_cmake_library = cmake.subproject('CMakeLibrary', options: cmake_opts)
my_cmake_dep = my_cmake_library.dependency('CMakeTarget')
# Link with CMakeLibrary::CMakeTarget
addon = napi.extension_module(
  'my_addon',
  [ 'src/my_source.cc' ],
  dependencies: [ my_cmake_dep ]
  )
```

You will also need to install the `CMake` xPack:

```shell
npx xpm install @xpack-dev-tools/cmake
```

#### `CMake` + WASM

You will need to pass the `emscripten` `CMake` toolchain to `meson` in the cross file.

`emscripten-wasm32.ini`:
```ini
[properties]
cmake_toolchain_file = '/<path_to_emsdk>/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'
```

## Add build options

If the project includes conditional compilation options, these can be transformed to `meson` build options.

Create a `meson.options` file:

```
option('async', type : 'boolean', value : true)
```

This `meson` option, `true` by default, can be activated by using `-Dasync=false`. It will also be set by the `import('node-api')` statement if `npm_config_enable_async` or `npm_config_disable_async` are found in the environment. This means that your user could type:

```shell
npm install your-module --disable-async
```

and this option will get passed to the meson build automatically where its value can be retrieved by using:

```python
if get_option('async')
   ...
endif
```

## Add `conan`

`hadron` supports `conan` out of the box. Simply add the `conan` xPack:

```shell
npx xpm install @mmomtchev/conan-xpack
```

Then create your `conanfile.txt` and add a `conan` step in the `xpm` build.

`conanfile.txt` with `zlib`:
```ini
[requires]
zlib/[>=1.2.0]

[generators]
# This is the conan + meson interaction
# as described in their own documentation
MesonToolchain
PkgConfigDeps

[tool_requires]
# Because of Windows
pkgconf/2.1.0
```

Add the `conan` prepare step to the build:

```json
{
  ...
  "properties": {
    "commandConanBuildEnv": {
      "win32": "build\\conanbuild.bat && ",
      "linux": ". build/conanbuild.sh && ",
      "darwin": ". build/conanbuild.sh && "
    }
  },
  "actions": {
    "build": "{{ properties.commandConanBuildEnv[os.platform] }} meson compile -C build -v",
    "prepare": [
      "conan install . -of build",
      "{{ properties.commandConanBuildEnv[os.platform] }} meson setup build . --native-file build{{ path.sep }}conan_meson_native.ini"
    ]
  }
  ...
}
```

There are a few new `xpm` elements here:
 * we are using command arrays that allow to run multiple commands per action
 * we are using the built-in LiquidJS templating engine that allows to expand variables from the `properties` section
 * we are using path separators that vary by OS with the `path.sep` constant
 * and we are using a special command that varies by OS as selected by the built-in `os.platform` constant

Finally, to link with this new dependency, import it in your `meson.build` and add it to the module:

```python
zlib_dep = dependency('zlib', method: 'pkg-config')
addon = napi.extension_module(
  'my_addon',
  [ 'src/my_source.cc' ],
  dependencies: [ zlib_dep ]
  )
```

#### `conan` + WASM

When using `conan` and WASM, you have two options:

 * get `emsdk` from `conan`, in which case `conan` will do everything for you, but you will be stuck with their version:

    `conanfile.txt`:
    ```
    [tool_requires]
    emsdk/3.1.50
    ```

 * install `emsdk` yourself

In both cases you will need a `conan` build profile:
`emscripten-wasm32.profile`:
```ini
[buildenv]
CC={{ os.getenv("EMCC") or "emcc" }}
CXX={{ os.getenv("EMCXX") or "em++" }}

[settings]
os=Emscripten
arch=wasm
compiler=clang
compiler.libcxx=libc++
compiler.version=17
```

`conan` will create your cross file for `meson`, and you won't need another WASM cross file.

This is how your WASM build action should look like:

```json
"wasm": {
  "actions": {
    "prepare": [
      "conan install . -of build -pr:h=emscripten-wasm32.profile --build=missing",
      "{{ properties.commandConanBuildEnv[os.platform] }} meson setup build . --cross-file build{{ path.sep }}conan_meson_cross.ini"
    ]
  }
}
```

[SWIG Node-API Example Project (`hadron`)](https://github.com/mmomtchev/hadron-swig-napi-example-project.git) uses the second option, it expects `emsdk` to be installed and activated in the environment.

#### `conan` + `CMake` (`CMake` subproject requires dependencies from `conan` )

You need to pass the `conan`-generated toolchain to the `meson` `cmake` module in a native or cross file:

`conan.ini`, to be passed to `meson`:
```
[properties]
cmake_toolchain_file = '@GLOBAL_BUILD_ROOT@' / 'conan_toolchain.cmake'
```

You should be aware that both `meson` and `conan` will pass their options to `CMake` - make sure that there are no conflicts. For example, `emscripten` cannot link monothreaded and multithreaded code, so do not make a monothreaded build on one side and a multithreaded build on the other side.

For the `cmake` module to pick the `conan` dependencies, `conan` should produce both `PkgConfigDeps` for `meson` and `CMakeDeps` to be consumed by the `CMake` project. As `conan` works best using the system default make (GNU `make`, `MSBuild.exe` or XCode) and `meson` always uses `ninja`, this requires some special configuration that is not possible in a `conanfile.txt` and must be in a `conanfile.py`.

[`magickwand.js`](https://github.com/mmomtchev/magickwand.js) is an example of a complex project that uses `conan` + `meson` + `CMake` + `emscripten`.

This is the relevant section of `conanfile.py`:

```python
from conan.tools.cmake import CMakeToolchain, CMakeDeps
generators = [ 'MesonToolchain', 'CMakeDeps' ]

    def generate(self):
        tc = CMakeToolchain(self)
        tc.blocks.remove("generic_system")
        tc.generate()
```

This is a custom `conan` generator that omits part of the generated `CMake` toolchain, allowing `hadron` to use its own `ninja` from its own xPack, while `conan` uses its own defaults - GNU `make`, `MSBuild.exe` and XCode. It is also possible to configure `conan` to use `ninja` everywhere, but my experience is that there will be a much higher risk of broken recipes and conflicts between the `ninja` from `conan` and the `ninja` from the xPack.


#### `conan` + build options

Check [`magickwand.js`](https://github.com/mmomtchev/magickwand.js) for a [`conanfile.py`](https://github.com/mmomtchev/magickwand.js/blob/meson/conanfile.py) that reads `npm install` options.

#### `conan` locking

It is recommended that real-world projects lock their dependencies - this is the `conan` equivalent of a `package-lock.json` - check [SWIG Node-API Example Project (`hadron`)](https://github.com/mmomtchev/hadron-swig-napi-example-project.git) for an example for `npx xpm lock --config native` action that creates a `conan` lock file.

#### `conan` + `CMake` + WASM interaction (a `hadron` with everything, please)

Also when using `conan` + `CMake` + WASM, the `emscripten` toolchain should be part of the `conan` toolchain which will pass it to `meson` which will pass it to `cmake`, here is the `conan` profile to use:

```ini
[buildenv]
CC={{ os.getenv("EMCC") or "emcc" }}
CXX={{ os.getenv("EMCXX") or "em++" }}

[settings]
os=Emscripten
arch=wasm
compiler=clang
compiler.libcxx=libc++
compiler.version=17

# This section is needed for conan + CMake + WASM
[conf]
tools.cmake.cmaketoolchain:user_toolchain=['{{ os.getenv("EMSDK") }}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake']
```

## Add prebuilt binaries and `npm install` scripts

`hadron` is compatible with both the original `prebuild-install` package and my own `@mmomtchev/prebuild-install` which includes some very minor changes such as up to date dependencies, `napi` mode by default and a built-in `build-wasm-from-source` option. A prebuilt binary is simply a `.tar.gz` that is decompressed at the root of the package when it is installed through `npm`. Typically binaries are built in `build/<config>` and are installed in `lib/binding` or `lib/binding/<platform>`. A prebuilt archive will need to include only `lib/binding`. Implementing the install scripts is possible through LiquidJS conditional templates.

Example relevant section from `package.json`:

```json
"xpack": {
  "properties": {
    "verbose": "{% if env.npm_config_loglevel %}--verbose{% endif %}",
    "scriptInstallNative": "npx prebuild-install -d {{ properties.verbose }} || ( npx xpm install && xpm run prepare --config native && xpm run build --config native )",
    "scriptInstallWASM": "npx prebuild-install --platform emscripten --arch wasm32 -d {{ properties.verbose }} || ( npx xpm install && xpm run prepare --config wasm && xpm run build --config wasm )"
  },
  "actions": {
    "npm-install": [
      "{% unless env.npm_config_skip_native_example %}{{ properties.scriptInstallNative }}{% endunless %}",
      "{% unless env.npm_config_skip_wasm_example %}{{ properties.scriptInstallWASM }}{% endunless %}"
    ]
  }
},
"binary": {
  "napi_versions": [ 6 ],
  "package_name": "{platform}-{arch}.tar.gz",
  "remote_path": "mmomtchev/hadron-swig-napi-example-project/releases/download/{tag_prefix}{version}/",
  "host": "https://github.com"
},
"scripts": {
  "install": "npx xpm run npm-install",
}
```

In this example, the `npm-install` `xpm` action can install prebuilt binaries. Both a native and a WASM version are installed in two separate steps. It won't do anything if `--skip-native-example` and/or `--skip-wasm-example` are passed - these options are useful for CI workflows that must build manually. If the user has specified `npm install ... --verbose --foreground-scripts`, then verbose mode is enabled. If `--build-from-source` and/or `--build-wasm-from-source` are passed, then `prebuild-install` will always rebuild instead of trying to download prebuilt binaries. The `binary` section contains the template to be used to construct the URL where the prebuilt package is located. Finally, everything is wired to run automatically when the user runs `npm install`.

## Advanced `node-api` options

The module supports a number of Node-API specific options (these are the default values):

```python
addon = napi.extension_module(
  'my_addon',
  [ 'src/my_source.cc' ],
  node_api_options: {
    'async_pool':               4,
    'es6':                      True,
    'stack':                    '2MB',
    'swig':                     False,
    'environments':             ['node', 'web', 'webview', 'worker'],
    'exported_functions':       ['_malloc', '_free', '_napi_register_wasm_v1', '_node_api_module_get_api_version_v1']',
    'exported_runtime_methods': ['emnapiInit']
  })
```

* `async_pool`: (*applies only to WASM*) sets the maximum number of simultaneously running async operations, must not exceed the `c_thread_count` / `cpp_thread_count` `meson` options which set the number of `emscripten` worker threads
* `es6`: (*applies only to WASM*) determines if `emscripten` will produce a CJS or ES6 WASM loader
* `stack`: (*applies only to WASM*) the maximum stack size, WASM cannot grow its stack
* `swig`: disables a number of warnings on the four major supported compilers (`gcc`, `clang`, `MSVC` and `emscripten`) triggered by the generated C++ code by SWIG
* `environments`: (*applies only to WASM*) determines the list of supported environments by the `emscripten` WASM loader, in particular, omitting `node` will produce a loader that does not work in Node.js, but can be bundled cleanly and without any extra configuration with most bundlers such as `webpack`
* `exported_functions`: (*applies only to WASM*) allows to modify the default list of exported functions to the WASM code
* `exported_runtime_methods`: (*applies only to WASM*) allows to modify the default list of WASM functions exported to JavaScript, typically the `FS` namespace can be added here to export the built-in filesystem API to JavaScript

## Advanced `xpm`, `meson` and `conan` options

Your further source of information should be their respective manuals.

`xpm` and `conan` are used completely unmodified. The xPacks allow you to use them seamlessly on all operating systems and without destroying any existing Python, `conan` or `meson` installations. This means that if you need access to their CLI options, you have to launch them through `xpm`.

Add a new action in your `package.json`:
```json
"actions": {
  "meson": "meson"
}
```

Then in order to modify the build configuration, launch:

```shell
npx xpm run meson -- configure build/
```

The `meson` core is modified from the original. It contains the new `node-api` module and a large number of improvements to the `conan` and `CMake` integration - something that does not work very well out of the box. Still, its manual remains completely valid.

# Why fork `meson`

Alas, the current state of my affair has made working with `conan` and `meson` extremely difficult.

In both projects, they tried to play a psychosis game with my work (my PRs) by doing simultaneously seemingly random acts and then trying to send me to see a psychiatrist. Given the context of the current affair, this has made any real work extremely difficult.

At the moment, both software packages need to be installed from my own repositories.
