## Fortran submodule support

Initial support for Fortran ``submodule`` was added, where the submodule is in the same or different file than the parent ``module``.
The submodule hierarchy must be specified in the source Fortran code `submodule` statements for it to be discovered by Meson, for example:

```fortran
submodule (ancestor:parent) child
```

