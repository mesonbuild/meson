## Fortran submodule support

Initial support for Fortran ``submodule`` was added, where the submodule is in
the same or different file than the parent ``module``.
The submodule hierarchy specified in the source Fortran code `submodule`
statements are used by Meson to resolve source file dependencies.
For example:

```fortran
submodule (ancestor:parent) child
```

