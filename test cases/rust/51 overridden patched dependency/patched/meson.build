patched_pkg = ws.package('patched')
patched_lib = patched_pkg.library(rust_abi: 'rust')
patched_pkg.override_dependency(declare_dependency(link_with: patched_lib))
