## Meson file rewriter

This release adds the functionality to perform some basic modification
on the `meson.build` files from the command line. The currently
supported operations are:

- For build targets:
  - Add/Remove source files
  - Add/Remove targets
  - Modify a select set of kwargs
  - Print some JSON information
- For dependencies:
  - Modify a select set of kwargs
- For the project function:
  - Modify a select set of kwargs
  - Modify the default options list

For more information see the rewriter documentation.
