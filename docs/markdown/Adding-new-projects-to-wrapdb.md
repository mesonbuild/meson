# Adding new projects to WrapDB


## How it works

Each wrap repository has a master branch with only one initial commit
and *no* wrap files. And that is the only commit ever made on that
branch.

For every release of a project a new branch is created. The new branch
is named after the the upstream release number (e.g. `1.0.0`). This
branch holds a wrap file for this particular release.

There are two types of wraps on WrapDB - regular wraps and wraps with
Meson build definition patches. A wrap file in a repository on WrapDB
must have a name `upstream.wrap`.

Wraps with Meson build definition patches work in much the same way as
Debian: we take the unaltered upstream source package and add a new
build system to it as a patch. These build systems are stored as Git
repositories on GitHub. They only contain build definition files. You
may also think of them as an overlay to upstream source.

Whenever a new commit is pushed into GitHub's project branch, a new
wrap is generated with an incremented version number. All the old
releases remain unaltered. New commits are always done via GitHub
merge requests and must be reviewed by someone other than the
submitter.

Note that your Git repo with wrap must not contain the subdirectory of
the source release. That gets added automatically by the service. You
also must not commit any source code from the original tarball into
the wrap repository.

## Choosing the repository name

Wrapped subprojects are used much like external dependencies. Thus
they should have the same name as the upstream projects.

NOTE: Repo names must fully match this regexp: `[a-z0-9._]+`.

If the project provides a pkg-config file, then the repository name
should be the same as the pkg-config name. Usually this is the name of
the project, such as `libpng`. Sometimes it is slightly different,
however. As an example the libogg project's chosen pkg-config name is
`ogg` instead of `libogg`, which is the reason why the repository is
named plain `ogg`.

If there is no a pkg-config file, the name the project uses/promotes
should be used, lowercase only (Catch2 -> catch2).

If the project name is too generic or ambiguous (e.g. `benchmark`),
consider using `organization-project` naming format (e.g.
`google-benchmark`).

## How to contribute a new wrap

If the project already uses Meson build system, then only a wrap file
- `upstream.wrap` should be provided. In other case a Meson build
definition patch - a set of `meson.build` files - should be also
provided.

### Request a new repository

*Note:* you should only do this if you have written the build files
and want to contribute them for inclusion to WrapDB. The maintainers
have only limited reesources and unfortunately can not take requests
to write Meson build definitions for arbitrary projects.

The submission starts by creating an issue on the [wrapdb bug
tracker](https://github.com/mesonbuild/wrapdb/issues) using *Title*
and *Description* below as a template.

*Title:* `new wrap: <project_name>`

*Description:*
```
upstream url: <link_to_updastream>
version: <version_you_have_a_wrap_for>
```

Wait until the new repository or branch is created. A link to the new
repository or branch will be posted in a comment to this issue. After
this you can createa a merge request in that repository for your build
files.

NOTE: Requesting a branch is not necessary. WrapDB maintainer can
create the branch and modify the PR accordingly if the project
repository exists.

### Creating the wrap contents

Setting up the contents might seem a bit counterintuitive at first.
Just remember that the outcome needs to have one (and only one) commit
that has all the build definition files (i.e. `meson.build` and
`meson_options.txt` files) and _nothing else_. It is good practice to
have this commit in a branch whose name matches the release as
described above.

First you need to fork the repository to your own page using GitHub's
fork button. Then you can clone the repo to your local machine.


```
git clone git@github.com:yourusername/libfoo.git foo-wrap
```

Create a new branch for your work:

```
git checkout -b 1.0.0
```

If you are adding new changes to an existing branch, leave out the
`-b` argument.

Now you need to copy the source code for the original project to this
directory. If you already have it extracted somewhere, you'd do
something like this:

```
cd /path/to/source/extract/dir
cp -r * /path/to/foo-wrap
```

Now all the files should be in the wrap directory. Do _not_ add them
to Git, though. Neither now or at any time during this process. The
repo must contain only the newly created build files.

New release branches require an `upstream.wrap` file, so create one if
needed.

```
${EDITOR} upstream.wrap
```

The file format is simple, see any existing wrapdb repo for the
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
Meson's automatic dependency resolver work. It is done by adding a
`provide` entry at the end of the `upstream.wrap` file. Using the Ogg
library as an example, this is what it would look like:

```ini
[provide]
ogg = ogg_dep
```

The `ogg` part on the left refers to the dependency name, which should
be the same as its Pkg-Config name. `ogg_dep` on the right refers to
the variable in the build definitions that provides the dependency.
Most commonly it holds the result of a `declare_dependency` call. If a
variable of that name is not defined, Meson will exit with a hard
error. For further details see [the main Wrap
manual](Wrap-dependency-system-manual.md).

Now you can create the build files and work on them until the project
builds correctly.

```
${EDITOR} meson.build meson_options.txt
```

When you are satisfied with the results, add the build files to Git
and push the result to GitHub.

```
<verify that your project builds and runs>
git add upstream.wrap meson.build
git commit -a -m 'Add wrap files for libfoo-1.0.0'
git push -u origin 1.0.0
```

Now you should create a pull request on GitHub. Try to create it
against the correct branch rather than master (`1.0.0` branch in this
example). GitHub should do this automatically.

If the branch doesn't exist file a pull request against master.
WrapDB maintainers can fix it before merging.

If packaging review requires you to do changes, use the `--amend`
argument to `commit` so that your branch will continue to have only
one commit.

```
${EDITOR} meson.build
git commit -a --amend
git push --force
```

### Request a new release version to an existing repository

Adding new releases to an existing repo is straightforward. All you
need to do is to follow the rules discussed above but when you create
the merge request, file it against the master branch. The repository
reviewer will create the necessary branch and retarget your merge
request accordingly.

## What is done by WrapDB maintainers

[mesonwrap tools](Wrap-maintainer-tools.md) must be used for the tasks
below.

### Adding new project to the Wrap provider service

Each project gets its own repo. It is initialized like this:

```
mesonwrap new_repo --homepage=$HOMEPAGE --directory=$NEW_LOCAL_PROJECT_DIR $PROJECT_NAME
```

The command creates a new repository and uploads it to GitHub.

`--version` flag may be used to create a branch immediately.

### Adding a new branch to an existing project

Create a new branch whose name matches the upstream release number.

```
git checkout master
git checkout -b 1.0.0
git push origin 1.0.0
(or from GitHub web page, remember to branch from master)
```

Branch names must fully match this regexp: `[a-z0-9._]+`.

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

Instructions on how to install and run the review tool can be found on
the [Wrap review guidelines page](Wrap-review-guidelines.md).  If your
submission is merge request number 5 for a repository called `mylib`,
then you'd run the following command:

    mesonwrap review --pull-request 5 mylib
