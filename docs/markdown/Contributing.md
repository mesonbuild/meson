---
short-description: Contributing to Meson
...

# Contributing to Meson

A large fraction of Meson is contributed by people outside the core
team. This documentation explains some of the design rationales of
Meson as well as how to create and submit your patches for inclusion
to Meson.

Thank you for your interest in participating to the development.

## Submitting patches

All changes must be submitted as [pull requests to
Github](https://github.com/mesonbuild/meson/pulls). This causes them
to be run through the CI system. All submissions must pass a full CI
test run before they are even considered for submission.

## Keeping pull requests up to date

It is possible that while your pull request is being reviewed, other
changes are committed to master that cause merge conflicts that must
be resolved. The basic rule for this is very simple: keep your pull
request up to date using rebase _only_.

Do not merge head back to your branch. Any merge commits in your pull
request make it not acceptable for merging into master and you must
remove them.

## Special procedure for new features

Every new feature requires some extra steps, namely:

 - Must include a project test under `test cases/`, or if that's not
   possible or if the test requires a special environment, it must go
   into `run_unittests.py`.
 - Must be registered with the [FeatureChecks framework](Release-notes-for-0.47.0.md#Feature_detection_based_on_meson_version_in_project)
   that will warn the user if they try to use a new feature while
   targetting an older meson version.
 - Needs a release note snippet inside `docs/markdown/snippets/` with
   a heading and a brief paragraph explaining what the feature does
   with an example.

## Acceptance and merging

The kind of review and acceptance any merge proposal gets depends on
the changes it contains. All pull requests must be reviewed and
accepted by someone with commit rights who is not the original
submitter. Merge requests can be roughly split into three different
categories.

The first one consists of MRs that only change the markdown
documentation under `docs/markdown`. Anyone with access rights can
push changes to these directly to master. For major changes it is
still recommended to create a MR so other people can comment on it.

The second group consists of merges that don't change any
functionality, fixes to the CI system and bug fixes that have added
regression tests (see below) and don't change existing
functionality. Once successfully reviewed anyone with merge rights can
merge these to master.

The final kind of merges are those that add new functionality or
change existing functionality in a backwards incompatible way. These
require the approval of the project lead.

In a simplified list form the split would look like the following:

 - members with commit access can do:
   - documentation changes (directly to master if warranted)
   - bug fixes that don't change functionality
   - refactorings
   - new dependency types
   - new tool support (e.g. a new Doxygen-kind of tool)
   - support for new compilers to existing languages
 - project leader decision is needed for:
   - new modules
   - new functions in the Meson language
   - syntax changes for Meson files
   - changes breaking backwards compatibility
   - support for new languages

## Strategy for merging pull requests to trunk

Meson's merge strategy should fullfill the following guidelines:

- preserve as much history as possible

- have as little junk in the repo as possible

- everything in the "master lineage" should always pass all tests

These goals are slightly contradictory so the correct thing to do
often requires some judgement on part of the person doing the
merge. Github provides three different merge options, The rules of
thumb for choosing between them goes like this:

 - single commit pull requests should always be rebased

 - a pull request with one commit and one "fixup" commit (such as
   testing something to see if it passes CI) should be squashed

 - large branches with many commits should be merged with a merge
   commit, especially if one of the commits does not pass all tests
   (which happens in e.g. large and difficult refactorings)

If in doubt, ask for guidance on IRC.

## Tests

All new features must come with automatic tests that thoroughly prove
that the feature is working as expected. Similarly bug fixes must come
with a unit test that demonstrates the bug, proves that it has been
fixed and prevents the feature from breaking in the future.

Sometimes it is difficult to create a unit test for a given bug. If
this is the case, note this in your pull request. We may permit bug
fix merge requests in these cases. This is done on a case by case
basis. Sometimes it may be easier to write the test than convince the
maintainers that one is not needed. Exercise judgment and ask for help
in problematic cases.

The tests are split into two different parts: unit tests and full
project tests. To run all tests, execute `./run_tests.py`. Unit tests
can be run with `./run_unittests.py` and project tests with
`./run_project_tests.py`.

Each project test is a standalone project that can be compiled on its
own. They are all in `test cases` subdirectory. The simplest way to
run a single project test is to do something like `./meson.py test\
cases/common/1\ trivial builddir`. The one exception to this is `test
cases/unit` directory discussed below.

The test cases in the `common` subdirectory are meant to be run always
for all backends. They should only depend on C and C++, without any
external dependencies such as libraries. Tests that require those are
in the `test cases/frameworks` directory. If there is a need for an
external program in the common directory, such as a code generator, it
should be implemented as a Python script. The goal of test projects is
also to provide sample projects that end users can use as a base for
their own projects.

All project tests follow the same pattern: they are compiled, tests
are run and finally install is run. Passing means that building and
tests succeed and installed files match the `installed_files.txt` file
in the test's source root. Any tests that require more thorough
analysis, such as checking that certain compiler arguments can be
found in the command line or that the generated pkg-config files
actually work should be done with a unit test.

Projects needed by unit tests are in the `test cases/unit`
subdirectory. They are not run as part of `./run_project_tests.py`.

### Skipping integration tests

Meson uses several continuous integration testing systems that have slightly
different interfaces for indicating a commit should be skipped.

Continuous integration systems currently used:
- [Travis-CI](https://docs.travis-ci.com/user/customizing-the-build#skipping-a-build)
  allows `[skip ci]` anywhere in the commit messages.
- [Azure Pipelines](https://docs.microsoft.com/en-us/azure/devops/pipelines/scripts/git-commands?view=vsts&tabs=yaml#how-do-i-avoid-triggering-a-ci-build-when-the-script-pushes)
  allows `***NO_CI***` in the commit message.
- [Sider](https://sider.review)
  runs Flake8 ([see below](#python-coding-style))

To promote consistent naming policy, use:

   - `[skip ci]` in the commit title if you want to disable all integration tests

## Documentation

The `docs` directory contains the full documentation that will be used
to generate [the Meson web site](http://mesonbuild.com). Every change
in functionality must change the documentation pages. In most cases
this means updating the reference documentation page but bigger
changes might need changes in other documentation, too.

All new functionality needs to have a mention in the release
notes. These features should be written in standalone files in the
`docs/markdown/snippets` directory. The release manager will combine
them into one page when doing the release.

[Integration tests should be disabled](#skipping-integration-tests) for
documentation-only commits by putting `[skip ci]` into commit title.
Reviewers should ask contributors to put `[skip ci]` into the title because
tests are run again after merge for `master`.

## Python Coding style

Meson follows the basic Python coding style. Additional rules are the
following:

- indent 4 spaces, no tabs ever
- indent meson.build files with two spaces
- try to keep the code as simple as possible
- contact the mailing list before embarking on large scale projects
  to avoid wasted effort

Meson uses Flake8 for style guide enforcement. The Flake8 options for
the project are contained in setup.cfg.

To run Flake8 on your local clone of Meson:

```console
$ python3 -m pip install flake8
$ cd meson
$ flake8
```

To run it automatically before committing:

```console
$ flake8 --install-hook=git
$ git config --bool flake8.strict true
```

## C/C++ coding style

Meson has a bunch of test code in several languages. The rules for
those are simple.

- indent 4 spaces, no tabs ever
- brace always on the same line as if/for/else/function definition



## External dependencies

The goal of Meson is to be as easily usable as possible. The user
experience should be "get Python3 and Ninja, run", even on
Windows. Unfortunately this means that we can't have dependencies on
projects outside of Python's standard library. This applies only to
core functionality, though. For additional helper programs etc the use
of external dependencies may be ok. If you feel that you are dealing
with this kind of case, please contact the developers first with your
use case.

## Turing completeness

The main design principle of Meson is that the definition language is
not Turing complete. Any change that would make Meson Turing complete
is automatically rejected. In practice this means that defining your
own functions inside `meson.build` files and generalised loops will
not be added to the language.

## Do I need to sign a CLA in order to contribute?

No you don't. All contributions are welcome.

## No lingering state

Meson operates in much the same way as functional programming
languages. It has inputs, which include `meson.build` files, values of
options, compilers and so on. These are passed to a function, which
generates output build definition. This function is pure, which means that:

 - for any given input the output is always the same
 - running Meson twice in a row _always_ produce the same output in both runs

The latter one is important, because it enforces that there is no way
for "secret state" to pass between consecutive invocations of
Meson. This is the reason why, for example, there is no `set_option`
function even though there is a `get_option` one.

If this were not the case, we could never know if the build output is
"stable". For example suppose there were a `set_option` function and a
boolean variable `flipflop`. Then you could do this:

```meson
set_option('flipflop', not get_option('flipflop'))
```

This piece of code would never converge. Every Meson run would change
the value of the option and thus the output you get out of this build
definition would be random.

Meson does not permit this by forbidding these sorts of covert channels.

There is one exception to this rule. Users can call into external
commands with `run_command`. If the output of that command does not
behave like a pure function, this problem arises. Meson does not try
to guard against this case, it is the responsibility of the user to
make sure the commands they run behave like pure functions.

## Environment variables

Environment variables are like global variables, except that they are
also hidden by default. Envvars should be avoided whenever possible,
all functionality should be exposed in better ways such as command
line switches.
