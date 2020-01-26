# Adding new projects to WrapDB


## How it works

Each wrap repository has a master branch with only one initial commit and *no* wrap files.
And that is the only commit ever made on that branch.

For every release of a project a new branch is created. The new branch is named after the 
the upstream release number (e.g. `1.0.0`). This branch holds a wrap file for 
this particular release.

There are two types of wraps on WrapDB - regular wraps and wraps with Meson build
definition patches. A wrap file in a repository on WrapDB must have a name `upstream.wrap`.

Wraps with Meson build definition patches work in much the same way as Debian: we take the unaltered upstream source package and add a new build system to it as a patch. These build systems are stored as Git repositories on GitHub. They only contain build definition files. You may also think of them as an overlay to upstream source.

Whenever a new commit is pushed into GitHub's project branch, a new wrap is generated
with an incremented version number. All the old releases remain unaltered.
New commits are always done via GitHub merge requests and must be reviewed by
someone other than the submitter.

Note that your Git repo with wrap must not contain the subdirectory of the source
release. That gets added automatically by the service. You also must not commit 
any source code from the original tarball into the wrap repository.

## Choosing the repository name

Wrapped subprojects are used much like external dependencies. Thus
they should have the same name as the upstream projects. 

If the project provides a pkg-config file, then the repository name should be
the same as the pkg-config name. Usually this is the name of the
project, such as `libpng`. Sometimes it is slightly different,
however. As an example the libogg project's chosen pkg-config name is
`ogg` instead of `libogg`, which is the reason why the repository is
named plain `ogg`.

If there is no a pkg-config file, the name the project uses/promotes should be used, 
lowercase only (Catch2 -> catch2).

## How to contribute a new wrap

If the project already uses Meson build system, then only a wrap file - `upstream.wrap`
should be provided. In other case a Meson build definition patch - a set of `meson.build` 
files - should be also provided.

### Request a new repository or branch

Create an issue on the [wrapdb bug tracker](https://github.com/mesonbuild/wrapdb/issues)
using *Title* and *Description* below as a template.

*Title:* `new wrap: <project_name>`

*Description:*
```
upstream url: <link_to_updastream>
version: <version_you_have_a_wrap_for>
```

Wait until the new repository or branch is created. A link to the new repository or branch
will be posted in a comment to this issue.

### Add a new wrap

First you need to fork the repository to your own page.
Then you can create the first Wrap commit that usually looks something like this.

```
tar xzf libfoo-1.0.0.tar.gz
git clone -b 1.0.0 git@github.com:yourusername/libfoo.git tmpdir
mv tmpdir/.git libfoo-1.0.0
rm -rf tmpdir
cd libfoo-1.0.0
git reset --hard
emacs upstream.wrap meson.build
<verify that your project builds and runs>
git add upstream.wrap meson.build
git commit -a -m 'Add wrap files for libfoo-1.0.0'
git push origin 1.0.0
```

Now you should create a pull request on GitHub. Remember to create it against the 
correct branch rather than master (`1.0.0` branch in this example). GitHub should do 
this automatically.

## What is done by WrapDB maintainers

### Adding new project to the Wrap provider service

Each project gets its own repo. It is initialized like this:

```
git init
git add readme.txt
git add LICENSE.build
git commit -a -m 'Create project foobar'
git remote add origin <repo url>
git push -u origin master
```

Note that this is the *only* commit that will ever be made to master branch. All other commits are done to branches.

Repo names must fully match this regexp: `[a-z0-9._]+`.

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

## Creator script

The WrapDB repository has a
[helper script](https://github.com/mesonbuild/mesonwrap/blob/master/mesonwrap.py)
to generate new repositories, verify them and update them.

## Reviewing wraps

See [Wrap review guidelines](Wrap-review-guidelines.md).
