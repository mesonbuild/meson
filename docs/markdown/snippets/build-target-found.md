## New `build target` methods

The [`build target` object](Reference-manual.md#build-target-object) now supports
the following two functions, to ensure feature compatebility with
[`external program` objects](Reference-manual.html#external-program-object):

- `found()`: Always returns `true`. This function is meant
  to make executables objects feature compatible with
  `external program` objects. This simplifies
  use-cases where an executable is used instead of an external program.

- `path()`: **(deprecated)** does the exact same as `full_path()`.
  **NOTE:** This function is solely kept for compatebility
  with `external program` objects. It will be
  removed once the, also deprecated, corresponding `path()` function in the
  `external program` object is removed.
