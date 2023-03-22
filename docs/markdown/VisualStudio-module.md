---
short-description: VisualStudio solution generator module
authors:
  - name: Charles Brunet
    email: charles.brunet@optelgroup.com
    yeal: [2023]
    has-copyright: false
...

# Unstable VisualStudio module

This module provides support for the generation of VisualStudio projects (.vcxproj)
and solutions (.sln), for projects using the `ninja` backend. It allows to work with
meson projects in the VisualStudio IDE, while keeping the speed an convenience of
the `ninja` build system.

It is different from the `vs` backend because:
- it uses `ninja` instead of `msbuild` a build system;
- you can select the project files you wnat to generate;
- project files preserve files hierarchy, and include header and meson.build files;
- you can generate different solution files, with selected project files;
- you can organise solution files with subdirectories for the different projects.

*Added 1.1.0*


## General usage

You create a [`vcxproj` object] for each build target you want configured into the
generated solution, using the `vs.project()` function. You configure
a [`sln` object] that includes all the [`vcxproj` object] you want, 
using the `vs.solution()` function.
Finally, you generate the `.sln` file using `sln.generate()` function. This will
generate `.vcxproj` files as well.


### Example

``` meson
project('myproject', 'cpp')

mylib_headers = files(...)
mylib = library('mylib', ...)
mylib_tests = executable(...)
test(mylib_tests, ...)

fs = import('fs')
vs = import('unstable-visualstudio')

mylib_vs_proj = vs.project(
    mylib,
    headers: mylib_headers,
)
mylib_test_proj = vs.project(
    mylib_tests
)

mylib_sol = vs.solution(
    'MyLib',
    projects: [mylib_vs_proj, mylib_test_proj]
)
mylib_sol.generate(
    output_dir: fs.parent(meson.global_build_root()) / 'vs'
)

```


## Functions

### `project()`

``` meson
vcxproj = vs.project(target,
    name: 'project name',
    config: 'release',
    subdir: 'subdir/path',
    sources: ['a.cpp', 'b.cpp', ...],
    headers: ['a.h', 'b.h', ...],
    extra_files: ['lib.rc', 'README.txt', ...],
    known_configurations: ['debug', 'release'],
    known_architectures: ['x64'],
)
```

Configure a new VisualStudio project, for the given target.

**Returns**: a [vcxproj][`vcxproj` object]

Include directories and defines (macros) are extracted from the given target (to help navigation in the IDE).
Architecture is detected from the host machine cpu_family. `x86_64` is translated to
`x64`, and `x86` is translated to `Win32`.
The use of debug libraries is detected from the `b_ndebug` option.
Toolset version is detected from the compiler version.
Other information is extracted as described below:

- `target`: a build target (library, shared_library, executable), an alias to a build target,
            or an internal dependency. In the case of an alias, the name of the alias is used,
            and all other information is taken from the pointed build target. In the case of
            a dependency object, `name` keyword must be provided. Dependency is mostly used for
            a header only project. It is also possible to create a project not linked to an
            actual target by omiting this argument. In that case, `name` keyword is mandatory.

- `name`: name used for the Vcxproj file. If not provided, target name will be used.
- `config`: name of the build config. If not provided, `buildtype` option will be used.
- `subdir`: if provided, project will be placed into `subdir` directory. This is also reflected
            in the generated solution.
- `sources`: by default, target sources are added to the project. This keyword is used to
             provide additional sources. Sources can be `str` or `File`.
- `headers`: header files to add to the project.
- `extra_files`: extra files from the target, `vs_module_defs`, and `meson.build` files are
                 automatically added as extra files. This keyword is used to provide additional
                 extra files (`str` or `File`).
- `known_configurations`: by default, generated vcxproj files will keep existing
                          configurations. If a list of configuations is provided here, only
                          those listed configurations are kept in the generated vcxproj file.
- `kwown_architectures`: by default, generated vcxproj files will keep existing
                          architectures. If a list of architectures is provided here, only
                          those listed architectures are kept in the generated vcxproj file.
                 
### `solution()`

``` meson
sol = vs.solution(name,
    projects: [proj1, proj2, ...],
    all: 'all')
```

Configure a new VisualStudio solution.

A solution is a group of related projects. 

**Returns**: a [sln][`sln` object]

- `name`: name used for the solution file
- `projects`: list of projects to include in the generated solution
- `all`: name of the target used to generate the solution (default: `'all'`)
         It can be a string, an `AliasTarget`, or a `BuildTarget`.
         Beware that **it is not** automatically computed from provided projects.
         You must provide an appropriate target if you dont want the solution
         to build the whole meson project.

`projects` can also be provided as a dict. In this case, each key is equivalent
to the `subdir` argument of the `add_project()` function.

``` meson
vs.solution('sol', {'': [rootproj, ...], 'subdir': subdirproj, 'path/to/other': [otherproj, ...]})
```



## Returned objects

### `vcxproj` object

Represents the configuration for a `.vcxproj` file. It is used to pass as an
argument to a [`sln` object].

#### `generate()`

``` meson
vcxproj.generate(output_dir: 'path/to/output')
```

Generates a single `.vcxproj` file. You usually don't need to call this method,
since the project will be generated when generating the solution. But for a simple
project, you may want a single project file, without generating a solution.

If `output_dir` is provided, the project files will be generated inside this directory.
Otherwise, project files are generated inside the current build directory.
If project has a `subdir`, it will be generated to `output_dir/subdir/`.

Three files a generated: `proj.vcxproj`, `proj.vcxproj.filters`, and `proj.vcxproj.user`.
The `.vcxproj` is the actual project, configured to be built using `ninja`.
The `.vcxproj.filters` group files in a hiearachy that mimics the filesystem.
The `.vcxproj.user` file is meant to be overriden by the user, and is never modified 
by the `generate()` function, once created.



### `sln` object

Represents the configucatoin for a `.sln` file.
You must call `generate()` on it to generate the actual files.


#### `add_project()`

``` meson
sln.add_project(vcxproj, subdir: 'subdir')
```

Add a project to the solution.

`vcxproj` is a project created using `vs.project()` function.

Optional `subdir` allow to group projects in the solution.
If project already has a `subdir` attribute, it will be placed
inside `subdir/vcxproj.subdir/`. However, this `subdir` is not used
for determining the directory where the `.vcxproj` files are generated.
It is only used for the logical organisation of the solution.


#### `generate()`

``` meson
sln.generate(
    output_dir: 'path/to/output',
    project_dir: 'path/to/projects'
)
```

Generate the actual solution and project files.

`output_dir`: Where the solution is generated. If not provided, current
build directory is used. If a relative path is provided, it is relative
to current build directory. 

You may provide a path ouside the current build directory, shared with
other configurations. When generating the solution file, existing configurations
are preserved, unless it is not specified in a project `know_configurations` or
`know_architectures` argument.

`project_dir` is where project files are gerated, relative to the `output_dir`.


For instance, if you have:

``` meson
p = vs.project(name: 'proj', subdir: 'p')
s = vs.solution('sol', {'s': p})
s.generate(
    output_dir: fs.parent(meson.global_build_root()),
    project_dir: 'projects',
)
```

resulting files will be like:

```
sol.sln
projects/
  p/
     proj.vcxproj
     proj.vcxproj.filters
     proj.vcxproj.user
debug/
release/
```

and resulting solution will be organized like:

```
s /
  p /
    proj.vcxproj
_ALL.vcxproj
```
