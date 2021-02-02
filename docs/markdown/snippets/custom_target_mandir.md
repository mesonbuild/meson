## `custom_target` accepts `'@MANDIR@'` for install_dirs

Until now there has been no nice way to handle generating man pages. Static
ones can be installed with `install_man`, which automatically detects the
extension of man pages and installs them to the right place. `custom_target`
lacked this, and the paths had to be manually calculated.

Now `'@MANDIR@'` can be used with `install_dir` to achieve the same effect:

```meson
custom_target(
    'man page',
    input : 'man.1.in',
    output : 'man.1',
    command : ...,
    install : true,
    install_dir : '@MANDIR@',
)
```
