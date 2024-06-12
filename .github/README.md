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

Install `node-addon-api` (if using C++):
```shell
npm install --save-dev node-addon-api
```

Install the `meson` and `ninja` xPacks:

```shell
xpm install @mmomtchev/meson-xpack @xpack-dev-tools/ninja-build
```

## Create the `meson.build` makefile

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

Crate a `meson` cross-file, the bare minimum is:

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

Then, the project will have to be modified to include build configurations:

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
    ..
}
```

The `build` step is common to both configuration, but from now on, when calling `prepare`, the configuration will have to be specified:

```shell
npx xpm run prepare --config wasm
npx xpm run build
```

Finally, install `emnapi`, add `c` as language in `project()` in `meson.build`, and launch your first WASM build:

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

## Advanced options

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

# Why fork `meson`

In fact, most of my projects are forks - I am currently in the middle of a huge judicial scandal, you can find more details on my main profile page, which involves corrupt criminal judges, the French police and some shocking sexual elements - which is the reason for the whole affair - at my previous employers. Currently, I am being extorted to accept to stop talking about this affair, by all the projects in which I have been working.

As I prefer to avoid dealing with criminal elements when working, I simply fork these projects. The `meson` project tried to play the schizophrenia game with my PR, then tried to convince me using various logical fallacies that I had gone insane and I was seeing things - including the extortion - which is precisely the same thing that happened with my two previous employers.

Should, for any project, their priorities shift from the criminal affair to their software, I will be willing submit my work as a single PR.

Obviously, I do not think that any normal working relation would ever be possible.
