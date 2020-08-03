# Wrap review guidelines

In order to get a package in the Wrap database it must be reviewed and
accepted by someone with admin rights. Here is a list of items to
check in the review. If some item is not met it does not mean that the
package is rejected. What should be done will be determined on a
case-by-case basis. Similarly meeting all these requirements does not
guarantee that the package will get accepted. Use common sense.

The review process is partially automated by the [mesonwrap](Wrap-maintainer-tools.md)
`review` tool.

```
mesonwrap review zlib --pull-request=1 [--approve]
```

Since not every check can be automated please pay attention to the following during the review:

- Download link points to an authoritative upstream location.
- Version branch is created from master.
- Except for the existing code, `LICENSE.build` is mandatory.
- `project()` has a version and it matches the source version.
- `project()` has a license.
- Complex `configure_file()` inputs are documented.
  If the file is a copy of a project file make sure it is clear what was changed.
- Unit tests are enabled if the project provides them.
- There are no guidelines if `install()` is a good or a bad thing in wraps.
- If the project can't be tested on the host platform consider using the `--cross-file` flag.
  See [the issue](https://github.com/mesonbuild/mesonwrap/issues/125).

Encourage wrap readability. Use your own judgement.

## Approval

If the code looks good use the `--approve` flag to merge it.
The tool automatically creates a release.
