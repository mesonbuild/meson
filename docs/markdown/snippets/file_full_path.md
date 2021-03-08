## file.full_path()

File objects now support a method called `full_path()`. It returns the full path
of the file.

```meson
srcs = files('x.c', 'y.c')
foreach s : srcs
  message(s.full_path()) # prints the full path of each file
endforeach
```
