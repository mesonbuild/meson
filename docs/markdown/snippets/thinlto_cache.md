## Incremental ThinLTO with `b_thinlto_cache`

[Incremental ThinLTO](https://clang.llvm.org/docs/ThinLTO.html#incremental) can now be enabled by passing
`-Db_thinlto_cache=true` during setup. The use of caching speeds up incremental builds significantly while retaining all
the runtime performance benefits of ThinLTO.

The cache location defaults to a Meson-managed directory inside the build folder, but can be customized with
`b_thinlto_cache_dir`.
