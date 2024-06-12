# `hadron` composite build system for C++/JavaScript Node-API modules

This is the core of the `hadron` build system for dual-environment Node.js/Browser C++/JavaScript Node-API modules

It consists of:
  * This modified `meson` core that includes:
    - A `node-api` module that greatly simplifies building dual-platform (native code in Node.js and WASM in the browser) C and C++ projects
    - Improved `CMake` compatibility with:
        * Support for `conan` `CMake` config files
        * Support for `$CONFIG` generator expressions
        * Support for `install_data(FILES ...)`
        * Several bugfixes related to handling the target dependencies
  * [`xpm`](https://xpack.github.io/xpm/) as build orchestrator and build software package manager
  * [`conan`](https://conan.io) as C/C++ package manager
  * [xPacks](https://xpack.github.io/) as standalone build packages

It is meant to be the preferred build system for [SWIG-JSE](https://github.com/mmomtchev/swig)-generated projects.

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
* [Add `conan`](#add-conan)
* [`conan` + `meson` + `CMake`](#conan--meson--cmake-interaction)
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

You will need to pass the `emscripten` `CMake` toolchain to `meson` in the cross file:

`emscripten-wasm32.ini`:
```ini
[properties]
cmake_toolchain_file = '/<path_to_emsdk>/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'
```

## Add `conan`

`hadron` supports `conan` out of the box. Simply add the `conan` xPack:

```shell
npx xpm install @mmomtchev/conan-xpack
```

Then create your `conanfile.txt` and add a `conan` step in the `xpm` build:

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
      "{{ properties.commandConanBuildEnv[os.platform] }} meson setup build . --native-file build/conan_meson_native.ini"
    ]
  }
  ...
}
```

There are a few new `xpm` elements here:
 * we are using command arrays that allow to run multiple commands per action
 * we are using the built-in LiquidJS templating engine that allows to expand variables from the `properties` section
 * and we are using a special command declined by OS

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
      "{{ properties.commandConanBuildEnv[os.platform] }} meson setup build . --cross-file build/conan_meson_cross.ini"
    ]
  }
}
```

[SWIG Node-API Example Project (`hadron`)](https://github.com/mmomtchev/hadron-swig-napi-example-project.git) uses the second option, it expects `emsdk` to be installed and activated in the environment.

## `conan` + `meson` + `CMake` interaction

There are a few items that you need to be aware when using `conan` + `meson` + `CMake`.

First of all, you need to pass the `conan`-generated toolchain to the `meson` `cmake` module in a native or cross file:

`conan.ini`, to be passed to `meson`:
```
[properties]
cmake_toolchain_file = '@GLOBAL_BUILD_ROOT@' / 'conan_toolchain.cmake'
```

Then you should know that both `meson` and `conan` will pass their options to `CMake` - make sure that those are the same. For example, do not make a monothreaded build on one side and a multithreaded build on the other - as `emscripten` cannot link monothreaded and multithreaded code.

[`magickwand.js`](https://github.com/mmomtchev/magickwand.js) is an example of a complex project that uses `conan` + `meson` + `CMake` + `emscripten`.

## Advanced `node-api` options

The module supports a number of Node-API specific options (these are the default values):

```python
addon = napi.extension_module(
  'my_addon',
  [ 'src/my_source.cc' ],
  node_api_options: {
    'async_pool':       4,
    'es6':              true,
    'stack':            '2MB',
    'swig':             false,
    'environments':     [ 'node', 'web', 'webview', 'worker' ]
  })
```

* `async_pool`: (*applies only to WASM*) sets the maximum number of simultaneously running async operations, must not exceed the `c_thread_count` / `cpp_thread_count` `meson` options which set the number of `emscripten` worker threads
* `es6`: (*applies only to WASM*) determines if `emscripten` will produce a CJS or ES6 WASM loader
* `stack`: (*applies only to WASM*) the maximum stack size, WASM cannot grow its stack
* `swig`: disables a number of warnings on the four major supported compilers (`gcc`, `clang`, `MSVC` and `emscripten`) triggered by the generated C++ code by SWIG
* `environments`: (*applies only to WASM*) determines the list of supported environments by the `emscripten` WASM loader, in particular, omitting `node` will produce a loader that does not work in Node.js, but can be bundled cleanly and without any extra configuration with most bundlers such as `webpack`

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

In fact, most of my projects are forks - I am currently in the middle of a huge judicial scandal, you can find more details on my main profile page, which involves corrupt criminal judges, the French police and some shocking sexual elements - which is the reason for the whole affair - at my previous employers. Currently, I am being extorted to accept to stop talking about this affair, by all the projects in which I have been working.

As I prefer to avoid dealing with criminal elements when working, I simply fork these projects. The `meson` project tried to play the schizophrenia game with my PR, then tried to convince me using various logical fallacies that I had gone insane and I was seeing things - including the extortion - which is precisely the same thing that happened with my two previous employers.

Should, for any project, their priorities shift from the criminal affair to their software, I will be willing submit my work as a single PR.

Obviously, I do not think that any normal working relation would ever be possible.
