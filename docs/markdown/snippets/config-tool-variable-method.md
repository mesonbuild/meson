# Config-Tool based dependencies gained a method to get arbitrary options

A number of dependencies (CUPS, LLVM, pcap, WxWidgets, GnuStep) use a config
tool instead of pkg-config. As of this version they now have a
`get_configtool_variable` method, which is analogous to the
`get_pkgconfig_variable` for pkg config.

```meson
dep_llvm = dependency('LLVM')
llvm_inc_dir = dep_llvm.get_configtool_variable('includedir')
```
