# Wrap dependency system manual

One of the major problems of multiplatform development is wrangling
all your dependencies. This is awkward on many platforms, especially
on ones that do not have a built-in package manager. The latter problem
has been worked around by having third party package managers. They
are not really a solution for end user deployment, because you can't
tell them to install a package manager just to use your app. On these
platforms you must produce self-contained applications. Same applies
when destination platform is missing (up-to-date versions of) your
application's dependencies.

The traditional approach to this has been to bundle dependencies
inside your own project. Either as prebuilt libraries and headers or
by embedding the source code inside your source tree and rewriting
your build system to build them as part of your project.

This is both tedious and error prone because it is always done by
hand. The Wrap dependency system of Meson aims to provide an automated
way to do this.

## How it works

Meson has a concept of [subprojects](Subprojects.md). They are a way
of nesting one Meson project inside another. Any project that builds
with Meson can detect that it is built as a subproject and build
itself in a way that makes it easy to use (usually this means as a
static library).

To use this kind of a project as a dependency you could just copy and
extract it inside your project's `subprojects` directory.

However there is a simpler way. You can specify a Wrap file that tells Meson
how to download it for you. If you then use this subproject in your build,
Meson will automatically download and extract it during build. This makes
subproject embedding extremely easy.

All wrap files must have a name of `<project_name>.wrap` form and be in `subprojects` dir.

Currently Meson has four kinds of wraps:
- wrap-file
- wrap-git
- wrap-hg
- wrap-svn

## wrap format

Wrap files are written in ini format, with a single header containing the type
of wrap, followed by properties describing how to obtain the sources, validate
them, and modify them if needed. An example wrap-file for the wrap named
`libfoobar` would have a filename `libfoobar.wrap` and would look like this:

```ini
[wrap-file]
directory = libfoobar-1.0

source_url = https://example.com/foobar-1.0.tar.gz
source_filename = foobar-1.0.tar.gz
source_hash = 5ebeea0dfb75d090ea0e7ff84799b2a7a1550db3fe61eb5f6f61c2e971e57663
```

An example wrap-git will look like this:

```ini
[wrap-git]
url = https://github.com/libfoobar/libfoobar.git
revision = head
```

## Accepted configuration properties for wraps
- `directory` - name of the subproject root directory, defaults to the name of the wrap.

Since *0.55.0* those can be used in all wrap types, they were previously reserved to `wrap-file`:

- `patch_url` - download url to retrieve an optional overlay archive
- `patch_fallback_url` - fallback URL to be used when download from `patch_url` fails *Since: 0.55.0*
- `patch_filename` - filename of the downloaded overlay archive
- `patch_hash` - sha256 checksum of the downloaded overlay archive
- `patch_directory` - *Since 0.55.0* Overlay directory, alternative to `patch_filename` in the case
  files are local instead of a downloaded archive. The directory must be placed in
  `subprojects/packagefiles`.

### Specific to wrap-file
- `source_url` - download url to retrieve the wrap-file source archive
- `source_fallback_url` - fallback URL to be used when download from `source_url` fails *Since: 0.55.0*
- `source_filename` - filename of the downloaded source archive
- `source_hash` - sha256 checksum of the downloaded source archive
- `lead_directory_missing` - for `wrap-file` create the leading
  directory name. Needed when the source file does not have a leading
  directory.

Since *0.55.0* it is possible to use only the `source_filename` and
`patch_filename` value in a .wrap file (without `source_url` and `patch_url`) to
specify a local archive in the `subprojects/packagefiles` directory. The `*_hash`
entries are optional when using this method. This method should be prefered over
the old `packagecache` approach described below.

Since *0.49.0* if `source_filename` or `patch_filename` is found in the
project's `subprojects/packagecache` directory, it will be used instead
of downloading the file, even if `--wrap-mode` option is set to
`nodownload`. The file's hash will be checked.

### Specific to VCS-based wraps
- `url` - name of the wrap-git repository to clone. Required.
- `revision` - name of the revision to checkout. Must be either: a
  valid value (such as a git tag) for the VCS's `checkout` command, or
  (for git) `head` to track upstream's default branch. Required.

### Specific to wrap-git
- `depth` - shallowly clone the repository to X number of commits. Note
  that git always allow shallowly cloning branches, but in order to
  clone commit ids shallowly, the server must support
  `uploadpack.allowReachableSHA1InWant=true`.  *(since 0.52.0)*
- `push-url` - alternative url to configure as a git push-url. Useful if
  the subproject will be developed and changes pushed upstream.
  *(since 0.37.0)*
- `clone-recursive` - also clone submodules of the repository
  *(since 0.48.0)*

## wrap-file with Meson build patch

Unfortunately most software projects in the world do not build with
Meson. Because of this Meson allows you to specify a patch URL.

For historic reasons this is called a "patch", however, it serves as an
overlay to add or replace files rather than modifying them. The file
must be an archive; it is downloaded and automatically extracted into
the subproject. The extracted files will include a meson build
definition for the given subproject.

This approach makes it extremely simple to embed dependencies that
require build system changes. You can write the Meson build definition
for the dependency in total isolation. This is a lot better than doing
it inside your own source tree, especially if it contains hundreds of
thousands of lines of code. Once you have a working build definition,
just zip up the Meson build files (and others you have changed) and
put them somewhere where you can download them.

Prior to *0.55.0* Meson build patches were only supported for wrap-file mode.
When using wrap-git, the repository must contain all Meson build definitions.
Since *0.55.0* Meson build patches are supported for any wrap modes, including
wrap-git.

## `provide` section

*Since *0.55.0*

Wrap files can define the dependencies it provides in the `[provide]` section.

```ini
[provide]
dependency_names = foo-1.0
```

When a wrap file provides the dependency `foo-1.0`, as above, any call to
`dependency('foo-1.0')` will automatically fallback to that subproject even if
no `fallback` keyword argument is given. A wrap file named `foo.wrap` implicitly
provides the dependency name `foo` even when the `[provide]` section is missing.

Optional dependencies, like `dependency('foo-1.0', required: get_option('foo_opt'))`
where `foo_opt` is a feature option set to `auto`, will not fallback to the
subproject defined in the wrap file, for 2 reasons:
- It allows for looking the dependency in other ways first, for example using
  `cc.find_library('foo')`, and only fallback if that fails:

```meson
# this won't use fallback defined in foo.wrap
foo_dep = dependency('foo-1.0', required: false)
if not foo_dep.found()
  foo_dep = cc.find_library('foo', has_headers: 'foo.h', required: false)
  if not foo_dep.found()
    # This will use the fallback
    foo_dep = dependency('foo-1.0')
    # or
    foo_dep = dependency('foo-1.0', required: false, fallback: 'foo')
  endif
endif
```

- Sometimes not-found dependency is preferable to a fallback when the feature is
  not explicitly requested by the user. In that case
  `dependency('foo-1.0', required: get_option('foo_opt'))` will only fallback
  when the user sets `foo_opt` to `enabled` instead of `auto`.

If it is desired to fallback for an optional dependency, the `fallback` keyword
argument must be passed explicitly. For example
`dependency('foo-1.0', required: get_option('foo_opt'), fallback: 'foo')` will
use the fallback even when `foo_opt` is set to `auto`.

This mechanism assumes the subproject calls `meson.override_dependency('foo-1.0', foo_dep)`
so Meson knows which dependency object should be used as fallback. Since that
method was introduced in version *0.54.0*, as a transitional aid for projects
that do not yet make use of it the variable name can be provided in the wrap file
with entries in the format `foo-1.0 = foo_dep`.

For example when using a recent enough version of glib that uses
`meson.override_dependency()` to override `glib-2.0`, `gobject-2.0` and `gio-2.0`,
a wrap file would look like:
```ini
[wrap-git]
url=https://gitlab.gnome.org/GNOME/glib.git
revision=glib-2-62

[provide]
dependency_names = glib-2.0, gobject-2.0, gio-2.0
```

With older version of glib dependency variable names need to be specified:
```ini
[wrap-git]
url=https://gitlab.gnome.org/GNOME/glib.git
revision=glib-2-62

[provide]
glib-2.0=glib_dep
gobject-2.0=gobject_dep
gio-2.0=gio_dep
```

Programs can also be provided by wrap files, with the `program_names` key:
```ini
[provide]
program_names = myprog, otherprog
```

With such wrap file, `find_program('myprog')` will automatically fallback to use
the subproject, assuming it uses `meson.override_find_program('myprog')`.

## Using wrapped projects

Wraps provide a convenient way of obtaining a project into your subproject directory.
Then you use it as a regular subproject (see [subprojects](Subprojects.md)).

## Getting wraps

Usually you don't want to write your wraps by hand.

There is an online repository called [WrapDB](https://wrapdb.mesonbuild.com) that provides
many dependencies ready to use. You can read more about WrapDB [here](Using-the-WrapDB.md).

There is also a Meson subcommand to get and manage wraps (see [using wraptool](Using-wraptool.md)).
