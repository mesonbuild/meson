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
extract it inside your project's `subprojects` directory. 

However there is a simpler way. You can specify a Wrap file that tells Meson
how to download it for you. If you then use this subproject in your build, 
Meson will automatically download and extract it during build. This makes
subproject embedding extremely easy.

All wrap files must have a name of `<project_name>.wrap` form and be in `subprojects` dir.

Currently Meson has three kinds of wraps: 
- wrap-file
- wrap-file with Meson build patch
- wrap-git

## wrap-file

An example wrap file for `libfoobar` would have a name `libfoobar.wrap` 
and would look like this:

```ini
[wrap-file]
directory = libfoobar-1.0

source_url = https://example.com/foobar-1.0.tar.gz
source_filename = foobar-1.0.tar.gz
source_hash = 5ebeea0dfb75d090ea0e7ff84799b2a7a1550db3fe61eb5f6f61c2e971e57663
```

`source_hash` is *sha256sum* of `source_filename`.

Since *0.49.0* if `source_filename` is found in project's
`subprojects/packagecache` directory, it will be used instead of downloading the
source, even if `--wrap-mode` option is set to `nodownload`. The file's hash will
be checked.

## wrap-file with Meson build patch

Unfortunately most software projects in the world do not build with
Meson. Because of this Meson allows you to specify a patch URL. This
works in much the same way as Debian's distro patches. That is, they
are downloaded and automatically applied to the subproject. These
files contain a Meson build definition for the given subproject. 

A wrap file with an additional patch URL would look like this:

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

Since *0.49.0* if `patch_filename` is found in project's
`subprojects/packagecache` directory, it will be used instead of downloading the
patch, even if `--wrap-mode` option is set to `nodownload`. The file's hash will
be checked.

## wrap-git

This type of wrap allows branching subprojects directly from git.

The above mentioned scheme assumes that your subproject is working off
packaged files. Sometimes you want to check code out directly from
Git. Meson supports this natively. All you need to do is to write a
slightly different wrap file.

```ini
[wrap-git]
directory = samplesubproject
url = https://github.com/jpakkane/samplesubproject.git
revision = head
```

The format is straightforward. The only thing to note is the revision
element that can have one of two values. The first is `head` which
will cause Meson to track the master head (doing a repull whenever the
build definition is altered). The second type is a commit hash or a
tag. In this case Meson will use the commit specified (with `git
checkout [hash/tag id]`).

Note that in this case you cannot specify an extra patch file to
use. The git repo must contain all necessary Meson build definitions.

Usually you would use subprojects as read only. However in some cases
you want to do commits to subprojects and push them upstream. For
these cases you can specify the upload URL by adding the following at
the end of your wrap file:

```ini
push-url = git@git.example.com:projects/someproject.git # Supported since version 0.37.0
```

If the git repo contains submodules, you can tell Meson to clone them
automatically by adding the following *(since 0.48.0)*:

```ini
clone-recursive = true
```

## Using wrapped projects

Wraps provide a convenient way of obtaining a project into your subproject directory. 
Then you use it as a regular subproject (see [subprojects](Subprojects.md)).

## Getting wraps

Usually you don't want to write your wraps by hand. 

There is an online repository called [WrapDB](https://wrapdb.mesonbuild.com) that provides 
many dependencies ready to use. You can read more about WrapDB [here](Using-the-WrapDB.md).

There is also a Meson subcommand to get and manage wraps (see [using wraptool](Using-wraptool.md)).
