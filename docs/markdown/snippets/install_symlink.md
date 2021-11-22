## install_symlink function

It is now possible to request for symbolic links to be installed during
installation. The `install_symlink` function takes a positional argument to
the link name, and installs a symbolic link pointing to `pointing_to` target.
The link will be created under `install_dir` directory and cannot contain path
separators.

```meson
install_symlink('target', pointing_to: '../bin/target', install_dir: '/usr/sbin')
```
