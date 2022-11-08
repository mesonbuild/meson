## External Project module

- New `build_by_default` keyword argument causes, when set to true, to have this
  target be built by default even when no other targets depends on it.

- New `kbuild()` method to build Linux kernel modules. By default it builds
  for the current kernel release, but the option
  `-Dexternal_project.kernel_build_dir=/path/x.y/build` can be used to use a
  different kernel tree.
```
epmod = import('unstable-external_project')
epmod.kbuild(build_by_default: true)
```
