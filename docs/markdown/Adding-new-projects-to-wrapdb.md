# Adding new projects to wrap

**If you don't have permissions to do something on this page, please
  open issue against https://github.com/mesonbuild/wrapweb/issues to
  let us know that you want to start new project.**

## Overview

The wrap provider service is a simple web service that makes it easy
to download build definitions for projects. It works in much the same
way as Debian: we take the unaltered upstream source package and add a
new build system to it as a patch. These build systems are stored as
Git repositories on GitHub. They only contain build definition
files. You may also think of them as an overlay to upstream source.

## Creator script

The WrapDB repository has a [helper
script](https://github.com/mesonbuild/wrapweb/blob/master/tools/repoinit.py)
to generate new repositories. The documentation below roughly explains
what it does using plain shell commands.

## Choosing the repository name

Wrapped subprojects are used much like external dependencies. Thus
they should have the same name as the upstream projects. If the
project provides a pkg-config file, then the repository name should be
the same as the pkg-config name. Usually this is the name of the
project, such as `libpng`. Sometimes it is slightly different,
however. As an example the libogg project's chosen pkg-config name is
`ogg` instead of `libogg`, which is the reason why the repository is
named plain `ogg`.

## Adding new project to the Wrap provider service

Each project gets its own repo. It is initialized like this:

    git init
    git add readme.txt
    git commit -a -m 'Start of project foobar.'
    git tag commit_zero -a -m 'A tag that helps get revision ids for releases.'
    git remote add origin <repo url>
    git push -u origin master
    git push --tags

Note that this is the *only* commit that will ever be made to master branch. All other commits are done to branches.

Repo names must fully match this regexp: `[a-z0-9._]+`.

## Adding a new branch to an existing project

Create a new branch whose name matches the upstream release number.

    git checkout master
    git checkout -b 1.0.0
    git push origin 1.0.0
    (or from GitHub web page, remember to branch from master)

Branch names must fully match this regexp: `[a-z0-9._]+`.

## Adding a new release to an existing branch

Here is where the magic happens. Whenever a new commit is pushed into GitHub's project branch, a new wrap is generated with an incremented version number. All the old releases remain unaltered. New commits are always done via GitHub merge requests and must be reviewed by someone other than the submitter.

Note that your Git repo must *not* contain the subdirectory of the source release. That gets added automatically by the service. You also must *not* commit any source code from the original tarball into the wrap repository.

First you need to fork the repository to your own page. Then you can create the first Wrap commit that usually looks something like this.

    tar xzf libfoo_1.0.0.tar.gz
    git clone -b 1.0.0 git@github.com:yourusername/libfoo.git tmpdir
    mv tmpdir/.git libfoo-1.0.0
    rm -rf tmpdir
    cd libfoo-1.0.0
    git reset --hard
    emacs upstream.wrap meson.build
    <verify that your project builds and runs>
    git add upstream.wrap meson.build
    git commit -a -m 'Created wrap files for libfoo-1.0.0.'
    git push origin 1.0.0

Now you can file a merge request. Remember to file it against branch
1.0.0 rather than master. GitHub should do this automatically.

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

## Reviewing wraps

See [Wrap review guidelines](Wrap-review-guidelines.md).
