# Adding new projects to WrapDB


## How it works

New wraps must be submitted as a working subproject to the [wrapdb
repository](https://github.com/mesonbuild/wrapdb).

There are two types of wraps on WrapDB - regular wraps and wraps with
Meson build definition patches.

Wraps with Meson build definition patches work in much the same way as
Debian: we take the unaltered upstream source package and add a new
build system to it as a patch. These build systems are stored as a
subdirectory of subprojects/packagefiles/. They only contain build
definition files. You may also think of them as an overlay to upstream
source.

Wraps without Meson build definition patches only contain the wrap
metadata describing how to fetch the project

Whenever a new release is pushed into the wrapdb, a new tag is
generated with an incremented version number, and a new release is
added to the wrapdb API listing. All the old releases remain
unaltered. New commits are always done via GitHub merge requests and
must be reviewed by someone other than the submitter.

Note that your Git repo with wrap must not contain the subdirectory of
the source release. That gets added automatically by the service. You
also must not commit any source code from the original tarball into
the wrap repository.

## Choosing the wrap name

Wrapped subprojects are used much like external dependencies. Thus
they should have the same name as the upstream projects.

NOTE: Wrap names must fully match this regexp: `[a-z0-9._]+`.

If the project provides a pkg-config file, then the wrap name
should be the same as the pkg-config name. Usually this is the name of
the project, such as `libpng`. Sometimes it is slightly different,
however. As an example the libogg project's chosen pkg-config name is
`ogg` instead of `libogg`, which is the reason why the wrap is
named plain `ogg`.

If there is no pkg-config file, the name the project uses/promotes
should be used, lowercase only (Catch2 -> catch2).

If the project name is too generic or ambiguous (e.g. `benchmark`),
consider using `organization-project` naming format (e.g.
`google-benchmark`).

## Overriding dependencies in the submitted project

Ideally the project you submit should make a call to `meson.override_dependency`
for each dependency you would like to expose, with the first argument
matching the pkg-config file name. This abstracts away the
need to know and keep track of the variable names downstream.

For instance, the Apache Arrow project exposes multiple dependencies like
its base `arrow` library, along with an `arrow-compute` library. The
project generates `arrow.pc` and `arrow-compute.pc` files for pkg-config
respectively, so internally the project also calls:

```meson
arrow_dep = declare_dependency(...)
meson.override_dependency('arrow', arrow_dep)

arrow_compute_dep = declare_dependency(...)
meson.override_dependency('arrow-compute', arrow_compute_dep)
```
Note that `meson.override_dependency` was introduced in Meson version
0.54.0. If your project supports older versions of Meson, you should
add a condition to only call that function in versions where it is
available:

```meson
if meson.version().version_compare('>=0.54.0')
    meson.override_dependency('arrow', arrow_dep)
    meson.override_dependency('arrow-compute', arrow_compute_dep)
endif
```

## How to contribute a new wrap

If the project already uses Meson build system, then only a wrap file
`project.wrap` should be provided. In other case a Meson build
definition patch - a set of `meson.build` files - should also be
provided.

### Creating the wrap contents

New release branches require a `project.wrap` file, so create one if
needed.

```
${EDITOR} upstream.wrap
```

The file format is simple, see any existing wrapdb subproject for the
content. The checksum is SHA-256 and can be calculated with the
following command on most unix-like operating systems:

```
sha256sum path/to/libfoo-1.0.0.tar.gz
```

Under macOS the command is the following:

```
shasum -a 256 path/to/libfoo-1.0.0.tar.gz
```

Next you need to add the entries that define what dependencies the
current project provides. This is important, as it is what makes
Meson's automatic dependency resolver work.

Assuming the project that you are creating
a wrap file for has called `meson.override_dependency`, then you
can declare those overridden dependencies in the `provide` section
of the wrap file:

```ini
[provide]
dependency_names = arrow, arrow_compute
```

In the case that you do not control the upstream Meson configuration
and it does not already make a call to `meson.override_dependency`,
then you can still expose dependency variables in the wrap file, using
a syntax like:

```ini
[provide]
arrow = arrow_dep
arrow_compute = arrow_compute_dep
```

The `arrow` and `arrow_compute` parts on the left refer to the dependency
names, which should be the same as their Pkg-Config name. `arrow_dep` and
`arrow_compute_dep` on the right refer to the variables in the build
definition that provide the dependencies. Most commonly, they hold the
result of a `declare_dependency` call. If a variable of that name is
not defined, Meson will exit with a hard error. For further details see
[the main Wrap manual](Wrap-dependency-system-manual.md).

However, it is strongly advised in such cases to request that the upstream
repository use `meson.override_dependency` for its next release, so that
the variable names chosen in the upstream configuration file can be
decoupled from the wrap file contents.

Now you can create the build files, if the upstream project does not
contain any, and work on them until the project builds correctly.
Remember that all files go in the directory
`subprojects/packagefiles/<project-name>`.

```
${EDITOR} meson.build meson.options
```

In order to apply the locally added build files to the upstream
release tarball, the `wrap-file` section must contain a
`patch_directory` property naming the subdirectory in
subprojects/packagefiles/ with the build files inside, as this is
central to the way the wrapdb works. It will be used by the wrapdb
meson.build, and when a release is created, the files from this
directory will be converted into an archive and a patch_url will be
added to the wrap file.

When you are satisfied with the results, add the build files to Git, update
releases.json as described in
[README.md](https://github.com/mesonbuild/wrapdb#readme), and push the result
to GitHub.

```
<verify that your project builds and runs>
git add releases.json subprojects/project.wrap subprojects/packagefiles/project/
git commit -a -m 'Add wrap files for libfoo-1.0.0'
git push -u origin libfoo
```

Now you should create a pull request on GitHub.

If packaging review requires you to do changes, use the `--amend`
argument to `commit` so that your branch will have only one commit.

```
${EDITOR} meson.build
git commit -u --amend
git push --force
```

## Changes to original source

The point of a wrap is to provide the upstream project with as few
changes as possible. Most projects should not contain anything more
than a few Meson definition files. Sometimes it may be necessary to
add a template header file or something similar. These should be held
at a minimum.

It should especially be noted that there must **not** be any patches
to functionality. All such changes must be submitted to upstream. You
may also host your own Git repo with the changes if you wish. The Wrap
system has native support for Git subprojects.

## Passing automatic validation

Every submitted wrap goes through an automated correctness review and
passing it is a requirement for merging. Therefore it is highly
recommended that you run the validation checks yourself so you can fix
any issues faster.

You can test the wrap itself with the following commands:

    meson subprojects purge --confirm
    meson setup builddir/ -Dwraps=<project-name>

The first command is to ensure the wrap is correctly fetched from the
latest packagefiles. The second command configures meson and selects a
set of subprojects to enable.

The GitHub project contains automatic CI on pushing to run the project
and check the metadata for obvious mistakes. This can be checked from
your fork before submitting a PR.
