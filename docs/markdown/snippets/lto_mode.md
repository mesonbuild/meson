## Support added for LLVM's thinLTO

A new `b_lto_mode` option has been added, which may be set to `default` or
`thin`. Thin only works for clang, and only with gnu gold, lld variants, or
ld64.
