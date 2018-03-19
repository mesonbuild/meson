## install_data() supports rename

`rename` parameter is used to change names of the installed files.
In order to install
- `file1.txt` into `share/myapp/dir1/data.txt`
- `file2.txt` into `share/myapp/dir2/data.txt`
```meson
install_data(['file1.txt', 'file2.txt'],
             rename : ['dir1/data.txt', 'dir2/data.txt'],
             install_dir : 'share/myapp')
```
