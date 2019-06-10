## Projects args can be set separately for build and host machines (potentially breaking change)

Simplify `native` flag behavior in `add_global_arguments`,
`add_global_link_arguments`, `add_project_arguments` and
`add_project_link_arguments`. The rules are now very simple:

 - `native: true` affects `native: true` targets

 - `native: false` affects `native: false` targets

 - No native flag is the same as `native: false`

This further simplifies behavior to match the "build vs host" decision done in
last release with `c_args` vs `build_c_args`. The underlying motivation in both
cases is to execute the same commands whether the overall build is native or
cross.
