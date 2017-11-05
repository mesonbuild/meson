# Wrap dependency system manual

One of the major problems of multiplatform development is wrangling
all your dependencies. This is easy on Linux where you can use system
packages but awkward on other platforms. Most of those do not have a
package manager at all. This has been worked around by having third
party package managers. They are not really a solution for end user
deployment, because you can't tell them to install a package manager
just to use your app. On these platforms you must produce
self-contained applications.

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
extract it inside your project's `subprojects` directory. However
there is a simpler way. You can specify a Wrap file that tells Meson
how to download it for you. An example wrap file would look like this
and should be put in `subprojects/foobar.wrap`:

```ini
[wrap-file]
directory = libfoobar-1.0

source_url = https://example.com/foobar-1.0.tar.gz
source_filename = foobar-1.0.tar.gz
source_hash = 5ebeea0dfb75d090ea0e7ff84799b2a7a1550db3fe61eb5f6f61c2e971e57663
```

If you then use this subproject in your build, Meson will
automatically download and extract it during build. This makes
subproject embedding extremely easy.

Unfortunately most software projects in the world do not build with
Meson. Because of this Meson allows you to specify a patch URL. This
works in much the same way as Debian's distro patches. That is, they
are downloaded and automatically applied to the subproject. These
files contain a Meson build definition for the given subproject. A
wrap file with an additional patch URL would look like this.

```ini
[wrap-file]
directory = libfoobar-1.0

source_url = https://upstream.example.com/foobar-1.0.tar.gz
source_filename = foobar-1.0.tar.gz
source_hash = 5ebeea0dfb75d090ea0e7ff84799b2a7a1550db3fe61eb5f6f61c2e971e57663

patch_url = https://myserver.example.com/libfoobar-meson.tar.gz
patch_filename = libfoobar-meson.tar.gz
patch_hash = 8c9d00702d5fe4a6bf25a36b821a332f6b2dfd117c66fe818b88b23d604635e9
```

In this example the Wrap manager would download the patch and unzip it
in libfoobar's directory.

This approach makes it extremely simple to embed dependencies that
require build system changes. You can write the Meson build definition
for the dependency in total isolation. This is a lot better than doing
it inside your own source tree, especially if it contains hundreds of
thousands of lines of code. Once you have a working build definition,
just zip up the Meson build files (and others you have changed) and
put them somewhere where you can download them.

## Branching subprojects directly from git

The above mentioned scheme assumes that your subproject is working off
packaged files. Sometimes you want to check code out directly from
Git. Meson supports this natively. All you need to do is to write a
slightly different wrap file.

```ini
[wrap-git]
directory=samplesubproject
url=https://github.com/jpakkane/samplesubproject.git
revision=head
```

The format is straightforward. The only thing to note is the revision
element that can have one of two values. The first is `head` which
will cause Meson to track the master head (doing a repull whenever the
build definition is altered). The second type is a commit hash. In
this case Meson will use the commit specified (with `git checkout
[hash id]`).

Note that in this case you cannot specify an extra patch file to
use. The git repo must contain all necessary Meson build definitions.

Usually you would use subprojects as read only. However in some cases
you want to do commits to subprojects and push them upstream. For
these cases you can specify the upload URL by adding the following at
the end of your wrap file:

```ini
push-url=git@git.example.com:projects/someproject.git # Supported since version 0.37.0
```

## Using wrapped projects

To use a subproject simply do this in your top level `meson.build`.

```meson
foobar_sp = subproject('foobar')
```

Usually dependencies consist of some header files plus a library to
link against. To do this you would declare this internal dependency
like this:

```meson
foobar_dep = declare_dependency(link_with : mylib,
  include_directories : myinc)
```

Then in your main project you would use them like this:

```meson
executable('toplevel_exe', 'prog.c',
  dependencies : foobar_sp.get_variable('foobar_dep'))
```

Note that the subproject object is *not* used as the dependency, but
rather you need to get the declared dependency from it with
`get_variable` because a subproject may have multiple declared
dependencies.

## Toggling between distro packages and embedded source

When building distro packages it is very important that you do not
embed any sources. Some distros have a rule forbidding embedded
dependencies so your project must be buildable without them or
otherwise the packager will hate you.

Doing this with Meson and Wrap is simple. Here's how you would use
distro packages and fall back to embedding if the dependency is not
available.

```meson
foobar_dep = dependency('foobar', required : false)

if not foobar_dep.found()
  foobar_subproj = subproject('foobar')
  # the subproject defines an internal dependency with
  # the command declare_dependency().
  foobar_dep = foobar_subproj.get_variable('foobar_dep')
endif

executable('toplevel_exe', 'prog.c',
  dependencies : foobar_dep)
```

Because this is such a common operation, Meson provides a shortcut for
this use case.

```meson
foobar_dep = dependency('foobar', fallback : ['foobar', 'foobar_dep'])
```

The `fallback` keyword argument takes two items, the name of the
subproject and the name of the variable that holds the dependency. If
you need to do something more complicated, such as extract several
different variables, then you need to do it yourself with the manual
method described above.

With this setup when foobar is provided by the system, we use it. When
that is not the case we use the embedded version. Note that
`foobar_dep` can point to an external or an internal dependency but
you don't have to worry about their differences. Meson will take care
of the details for you.

## Getting wraps

Usually you don't want to write your wraps by hand. There is an online
repository called [WrapDB](Using-the-WrapDB.md) that provides many
dependencies ready to use.
