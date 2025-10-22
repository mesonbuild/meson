---
short-description: Rust language integration module
authors:
    - name: Dylan Baker
      email: dylan@pnwbakers.com
      years: [2020, 2021, 2022, 2024]
    - name: Paolo Bonzini
      email: bonzini@gnu.org
      years: [2025]
...

# Rust module

*(new in 0.57.0)*
*(Stable since 1.0.0)*

The rust module provides helper to integrate rust code into Meson. The
goal is to make using rust in Meson more pleasant, while still
remaining mesonic, this means that it attempts to make Rust work more
like Meson, rather than Meson work more like rust.

## Functions

### test()

```meson
rustmod.test(name, target, ...)
```

This function creates a new rust unittest target from an existing rust
based target, which may be a library or executable. It does this by
copying the sources and arguments passed to the original target and
adding the `--test` argument to the compilation, then creates a new
test target which calls that executable, using the rust test protocol.

This function takes two positional arguments, the first is the name of the
test and the second is the library or executable that is the rust based target.
It also takes the following keyword arguments:

- `dependencies`: a list of test-only Dependencies
- `link_with`: a list of additional build Targets to link with (*since 1.2.0*)
- `link_whole`: a list of additional build Targets to link with in their entirety (*since 1.8.0*)
- `rust_args`: a list of extra arguments passed to the Rust compiler (*since 1.2.0*)

This function  also accepts all of the keyword arguments accepted by the
[[test]] function except `protocol`, it will set that automatically.

### doctest()

```meson
rustmod.doctest(name, target, ...)
```

*Since 1.8.0*

This function creates a new `test()` target from an existing rust
based library target. The test will use `rustdoc` to extract and run
the doctests that are included in `target`'s sources.

This function takes two positional arguments, the first is the name of the
test and the second is the library or executable that is the rust based target.
It also takes the following keyword arguments:

- `dependencies`: a list of test-only Dependencies
- `link_with`: a list of additional build Targets to link with
- `link_whole`: a list of additional build Targets to link with in their entirety
- `rust_args`: a list of extra arguments passed to the Rust compiler

The target is linked automatically into the doctests.

This function  also accepts all of the keyword arguments accepted by the
[[test]] function except `protocol`, it will set that automatically.
However, arguments are limited to strings that do not contain spaces
due to limitations of `rustdoc`.

### bindgen()

This function wraps bindgen to simplify creating rust bindings around C
libraries. This has two advantages over invoking bindgen with a
`generator` or `custom_target`:

- It handles `include_directories`, so one doesn't have to manually convert them to `-I...`
- It automatically sets up a depfile, making the results more reliable
- It automatically handles assertions, synchronizing Rust and C/C++ to have the same behavior


It takes the following keyword arguments

- `input`: a list of Files, Strings, or CustomTargets. The first element is
  the header bindgen will parse, additional elements are dependencies.
- `output`: the name of the output rust file
- `output_inline_wrapper`: the name of the optional output c file containing
  wrappers for static inline function. This requires `bindgen-0.65` or
  newer (*since 1.3.0*).
- `include_directories`: A list of `include_directories` or `string` objects,
  these are passed to clang as `-I` arguments *(string since 1.0.0)*
- `c_args`: a list of string arguments to pass to clang untouched
- `args`: a list of string arguments to pass to `bindgen` untouched.
- `dependencies`: a list of `Dependency` objects to pass to the underlying clang call (*since 1.0.0*)
- `language`: A literal string value of `c` or `cpp`. When set this will force bindgen to treat a source as the given language. Defaults to checking based on the input file extension. *(since 1.4.0)*
- `bindgen_version`: a list of string version values. When set the found bindgen binary must conform to these constraints. *(since 1.4.0)*

```meson
rust = import('unstable-rust')

inc = include_directories('..'¸ '../../foo')

generated = rust.bindgen(
    input : 'myheader.h',
    output : 'generated.rs',
    include_directories : [inc, include_directories('foo')],
    args : ['--no-rustfmt-bindings'],
    c_args : ['-DFOO=1'],
)
```

If the header depends on generated headers, those headers must be passed to
`bindgen` as well to ensure proper dependency ordering, static headers do not
need to be passed, as a proper depfile is generated:

```meson
h1 = custom_target(...)
h2 = custom_target(...)

r1 = rust.bindgen(
  input : [h1, h2],  # h1 includes h2,
  output : 'out.rs',
)
```

*Since 1.1.0* Meson will synchronize assertions for Rust and C/C++  when the
`b_ndebug` option is set (via `-DNDEBUG` for C/C++, and `-C
debug-assertions=on` for Rust), and will pass `-DNDEBUG` as an extra argument
to clang. This allows for reliable wrapping of `-DNDEBUG` controlled behavior
with `#[cfg(debug_asserions)]` and or `cfg!()`. Before 1.1.0, assertions for Rust
were never turned on by Meson.

*Since 1.2.0* Additional arguments to pass to clang may be specified in a
*machine file in the properties section:

```ini
[properties]
bindgen_clang_arguments = ['--target', 'x86_64-linux-gnu']
```

### proc_macro()

```meson
rustmod.proc_macro(name, sources, ...)
```

*Since 1.3.0*

This function creates a Rust `proc-macro` crate, similar to:
```meson
[[shared_library]](name, sources,
  rust_crate_type: 'proc-macro',
  native: true)
```

`proc-macro` targets can be passed to `link_with` keyword argument of other Rust
targets.

Only a subset of [[shared_library]] keyword arguments are allowed:
- rust_args
- rust_dependency_map
- sources
- dependencies
- extra_files
- link_args
- link_depends
- link_with
- override_options

### workspace()

Basic usage:

```
cargo_ws = rustmod.workspace()
```

With custom features:

```
feature_list = get_feature('f1') ? ['feature1'] : []
feature_list += get_feature('f2') ? ['feature2'] : []
cargo_ws = rustmod.workspace(features: feature_list)
```

*Since 1.11.0*

Create and return a `workspace` object for managing the project's Cargo
workspace.

Keyword arguments:
- `default_features`: (`bool`, optional) Whether to enable default features.
- `features`: (`list[str]`, optional) List of additional features to enable globally.

A project that wishes to use Cargo subprojects should have `Cargo.lock` and `Cargo.toml`
files in the root source directory, and should call this function before using
Cargo subprojects.

The first invocation of `workspace()` establishes the *Cargo interpreter*
that resolves dependencies and features for both the toplevel project (the one
containing `Cargo.lock`) and all subprojects that are invoked with the `cargo` method,

You can optionally customize the feature set, by providing `default_features`
and `features` when the Cargo interpreter is established.  If any of these
arguments is not specified, `default_features` is taken as `true` and
`features` as the empty list.

Once established, the Cargo interpreter's configuration is locked. Later calls to
`workspace()` must either omit all arguments (accepting the existing configuration)
or provide the same set of features as the first call. Mismatched arguments will cause
a build error.

The recommendation is to not specify any keyword arguments in a subproject, so
that they simply inherit the parent's configuration.  Be careful about the
difference between specifying arguments and not doing so:

```
# always works regardless of parent configuration
cargo_ws = rustmod.workspace()

# fails if parent configured different features
cargo_ws = rustmod.workspace(default_features: true)
cargo_ws = rustmod.workspace(features: [])
```

The first form says "use whatever features are configured," while the latter forms
say "require this specific configuration," which may conflict with the parent project.

## Workspace object

### workspace.packages()

```meson
packages = ws.packages()
```

Returns a list of package names in the workspace.

### workspace.subproject()

```meson
package = ws.subproject(package_name, api)
```

Returns a `package` object for managing a specific package within the workspace.

Positional arguments:
- `package_name`: (`str`) The name of the package to retrieve
- `api`: (`str`, optional) The version constraints for the package in Cargo format

## Package object

The package object returned by `workspace.subproject()` provides methods
for working with individual packages in a Cargo workspace.

### subproject.name()

```meson
name = pkg.name()
```

Returns the name of the subproject.

### subproject.version()

```meson
version = pkg.version()
```

Returns the normalized version number of the subproject.

### subproject.api()

```meson
api = pkg.api()
```

Returns the API version of the subproject, that is the version up to the first
nonzero element.

### subproject.features()

```meson
features = pkg.features()
```

Returns selected features for a specific subproject.

### subproject.all_features()

```meson
all_features = pkg.all_features()
```

Returns all defined features for a specific subproject.

### subproject.dependency()

```meson
dep = subproject.dependency(...)
```

Returns a dependency object for the subproject that can be used with other Meson targets.

*Note*: right now, this method is implemented on top of the normal Meson function
[[dependency]]; this is subject to change in future releases.  It is recommended
to always retrieve a Cargo subproject's dependency object via this method.

Keyword arguments:
- `rust_abi`: (`str`, optional) The ABI to use for the dependency. Valid values are
  `'rust'`, `'c'`, or `'proc-macro'`. The package must support the specified ABI.
