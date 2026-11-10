---
short-description: Common Code Generators Module
authors:
    - name: Dylan Baker
      email: dylan@pnwbakers.com
      years: [2024, 2025]
    - name: Charles Brunet
      email: charles.brunet@optelgroup.com
      years: [2026]
...

# Codegen Module

*(New in 1.10.0)*

This module provides wrappers around common code generators, such as flex/lex and yacc/bison. This purpose of this is to make it easier and more pleasant to use *common* code generators in a mesonic way.


## Functions

### lex()

```meson
lex_gen = codegen.lex(implementations : ['flex', 'reflex'], flex_version : ['>= 2.6', '< 3'], reflex_version : '!= 1.4.2')
```

This function provides fine grained control over what implementation(s) and version(s) of lex are acceptable for a given project (These are set per-subproject). It returns a [new object](#lexgenerator), which can be used to generate code.

It accepts the following keyword arguments:

 - `implementations`: a string array of acceptable implementations to use. May include: `lex`, `flex`, `reflex`, or `win_flex`.
 - `lex_version`: a string array of version constraints to apply to the `lex` binary
 - `flex_version`: a string array of version constraints to apply to the `flex` binary
 - `reflex_version`: a string array of version constraints to apply to the `relex` binary
 - `win_flex_version`: a string array of version constraints to apply to the `win_flex` binary
 - `required`: A boolean or feature option
 - `disabler`: Return a disabler if not found
 - `native`: Is this generator for the host or build machine?

### yacc()

```meson
yacc = codegen.yacc(implementations : ['bison', 'win_bison'])
```

This function provides fine grained controls over which implementation(s) and version(s) of the parser generator to use.

Accepts the following keyword arguments:

 - `implementations`: a string array of acceptable implementations to use. May include: `yacc`, `byacc`,  `bison`, or `win_bison`.
 - `yacc_version`: a string array of version constraints to apply to the `yacc` binary
 - `byacc_version`: a string array of version constraints to apply to the `byacc` binary
 - `bison_version`: a string array of version constraints to apply to the `bison` binary
 - `win_bison_version`: a string array of version constraints to apply to the `win_bison` binary
 - `required`: A boolean or feature option
 - `disabler`: Return a disabler if not found
 - `native`: Is this generator for the host or build machine?

### protoc()

*(New in 1.14.0)*

```meson
protoc = codegen.protoc(
  dependency: dependency('protobuf'),  # optional; needed for cpp
  version: '>=3.21', required: true, native: true,
)
```

This function finds the `protoc` protobuf compiler.

Accepts the following keyword arguments:

- `dependency`: the `protobuf` dependency. If not provided, meson will look for `dependency('protobuf')`.
- `grpc_dependency`: the gRPC dependency. When given and found,
                     the `grpc_cpp_plugin` program is looked up for the same machine as `protoc`
                     (honouring `meson.override_find_program()`), and `generate()` produces gRPC
                     files by default. If not provided, but `protoc.generate(grpc: true)` is called,
                     meson will look for `dependency('grpc++')`.
- `version`: a string array of version constraints to apply to the `protoc` binary.
- `native`: Is this generator for the host or build machine?
- `required`: A boolean or feature option.
- `disabler`: Return a disabler if not found.
- `import_dirs`: An array of include_directories or strings to add as `protoc` search paths,
                 relative to the current source dir.
- `args`: Additional arguments to give to `protoc`.

It returns a ProtocGenerator object.


## Returned Objects

### LexGenerator

#### lex.implementation

```meson
lex = codegen.lex()
impl = lex.implementation()
```

Returns the string name of the lex implementation chosen. May be one of:

- lex
- flex
- reflex
- win_flex

#### lex.generate

```meson
lex = codegen.lex()
lex.generate('lexer.l')
```

This function wraps flex, lex, reflex (but not RE/flex), and win_flex (on Windows). When using win_flex it will automatically add the `--wincompat` argument.

This requires an input file, which may be a string, File, or generated source. It additionally takes the following options keyword arguments:

- `args`: An array of extra arguments to pass the lexer
- `plainname`: If set to true then `@PLAINNAME@` will be used as the source base, otherwise `@BASENAME@`.
- `source`: the name of the source output. If this is unset Meson will use `{base}.{ext}` with an extension of `cpp` if the input has an extension of `.ll`, or `c` otherwise, with base being determined by the `plainname` argument.
- `header`: The optional output name for a header file. If this is unset no header is added
- `table`: The optional output name for a table file. If this is unset no table will be generated

The outputs will be in the form `source [header] [table]`, which means those can be accessed by indexing the output of the `lex` call:

```meson
lex = codegen.lex()
l1 = lex.generate('lexer.l', header : '@BASENAME@.h', table : '@BASENAME@.tab.h')
headers = [l1[1], l1[2]]  # [header, table]

l2 = lex.generate('lexer.l', table : '@BASENAME@.tab.h')
table = l2[1]
```

### YaccGenerator

#### yacc.implementation

```meson
yacc = codegen.yacc()
impl = yacc.implementation()
```

Returns the string name of the yacc implementation chosen. May be one of:

- yacc
- bison
- byacc
- win_bison

#### yacc.generate

```meson
yacc = codegen.yacc()
yacc.generate('parser.y')
```

This function wraps bison, yacc, byacc, and win_bison (on Windows), and attempts to abstract away the differences between them

This requires an input file, which may be a string, File, or generated source. It additionally takes the following options keyword arguments:

- `version`: Version constraints on the lexer
- `args`: An array of extra arguments to pass the lexer
- `plainname`: If set to true then `@PLAINNAME@` will be used as the source base, otherwise `@BASENAME@`.
- `source`: the name of the source output. If this is unset Meson will use `{base}.{ext}` with an extension of `cpp` if the input has an extension of `.yy` or `c` otherwise, with base being determined by the `plainname` argument.
- `header`: the name of the header output. If this is unset Meson will use `{base}.{ext}` with an extension of `hpp` if the input has an extension of `.yy` or `h` otherwise, with base being determined by the `plainname` argument.
- `locations`: The name of the locations file, if one is generated. Due to the way yacc works this must be duplicated in the file and in the command.

The outputs will be in the form `source header [locations]`, which means those can be accessed by indexing the output of the `yacc` call:

```meson
yacc = codegen.yacc()
p1 = yacc.generate('parser.y', header : '@BASENAME@.h', locations : 'locations.h')
headers = [p1[1], p1[2]]  # [header, locations]

p2 = yacc.generate('parser.yy', locations : 'locations.hpp')
locations = p2[1]
```

### ProtocGenerator

#### protoc.found

Returns `true` if the `protoc` binary was found.

#### protoc.version

Returns the `protoc` binary version.
Calling it when not found is an error.

#### protoc.generate

```meson
gen = protoc.generate('a/b/foo.proto', 'a/c/bar.proto',
  language: 'cpp',
  import_dirs: include_directories('other_protos'),
  install: true, install_dir: get_option('includedir'),
)
```

This function generates implementation files from .proto files for a specific
language. The directory where `generate()` is called is the root of its inputs:
the path of a proto file relative to that directory (or to the matching build
directory, for generated proto files) is its import name. Other proto files
must use this name in their import statements, and it determines where the
generated files go. For instance, for the input `a/b.proto`, code includes
`#include "a/b.pb.h"` and the header is installed to `<install_dir>/a/b.pb.h`;
the include root is provided by `gen.dependency()`. Therefore, you must call
`generate()` from the directory that is the root of your proto import paths.
Source and generated proto files share the same import names, so two inputs
with the same import name are an error.

`generate()` requires one or many proto input files, which may be strings, Files, custom_target,
or custom_idx. Inputs outside the current source dir (or current build dir) are an error.

It additionally takes the following options keyword arguments:

- `language`: For which language `protoc` will generate files. Only "cpp" is currently
              supported. Default value is "cpp".
- `import_dirs`: An array of include_directories or strings to add as `protoc` search paths,
                 relative to the current source dir. Protobufs from those directories
                 are not generated automatically; it is the user's responsibility to
                 ensure they are generated.
                 It combines with `import_dirs` from `codegen.protoc`.
- `imports`: An array of ProtocOutput when the generated protobuf depends on another
             protobuf generator, from a different directory or from a subproject, for instance.
             This ensures that the required search paths for compiling the protobuf are propagated,
             and that the dependency returned from the generated output also carries
             the imported dependencies. When a .proto file imports a .proto file provided by
             `imports`, the import must be relative to the imported proto root.
- `args`: Additional arguments to give to `protoc`. It combines with `args` from `codegen.protoc`.
- `install`: Add generated files to the install plan. For C++, it installs generated header files.
             Default is `false`.
- `install_dir`: Where to install generated files (headers for C++). Defaults to `includedir`.
- `grpc`: Also generate gRPC files (`foo.grpc.pb.cc` and `foo.grpc.pb.h` for C++), in the same
          `protoc` invocation, using `grpc_cpp_plugin`. They are generated for every input, even
          those without a service. Defaults to `true` if a found `grpc_dependency` was given to
          `codegen.protoc()`, `false` otherwise. Setting it to `true` will cause meson to look
          for the `grpc++` dependency if `grpc_dependency` was not provided. Only supported
          for the "cpp" language. The gRPC files are part of `sources()`, `headers()` and
          `dependency()`, which also carries the gRPC dependency, and are installed with the
          protobuf headers.

It returns a ProtocOutput.

Example:

```meson
# meson.build
codegen = import('unstable-codegen')
protoc = codegen.protoc(dependency: dependency('protobuf'))
subdir('protos')
executable('app', 'main.cpp', dependencies: gen.dependency())

# protos/meson.build
gen = protoc.generate('a/b/foo.proto')
```

### ProtocOutput

#### gen.dependency

Returns an internal dependency (for C++) with compile sources, include root and runtime dependencies.
That includes the protobuf dependency provided to `codegen.protoc()`.
Calling it when the language was not `cpp` triggers an error.

#### gen.sources

Returns an array of custom_idx from generated source files. To be used as `custom_target` inputs,
or with depends.

#### gen.headers

Returns an array of custom_idx from generated header files. To be used as `custom_target` inputs,
or with depends.
