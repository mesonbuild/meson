## `meson test` can now filter tests by subproject

You could always specify a list of tests to run by passing the names as
arguments to `meson test`. If there were multiple tests with that name (in the
same project or different subprojects), all of them would be run. Now you can:

1. Run all tests with the specified name from a specific subproject: `meson test subprojname:testname`
1. Run all tests defined in a specific subproject: `meson test subprojectname:`

As before, these can all be specified multiple times and mixed:

```sh
# Run:
# * All tests called 'name1' or 'name2' and
# * All tests called 'name3' in subproject 'bar' and
# * All tests in subproject 'foo'
$ meson test name1 name2 bar:name3 foo:
```
