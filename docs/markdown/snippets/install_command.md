## Made install a top level Meson command

You can now run `meson install` in your build directory and it will do
the install. It has several command line options you can toggle the
behaviour that is not in the default `ninja install` invocation. This
is similar to how `meson test` already works.

For example, to install only the files that have changed, you can do:

```console
meson install --only-changed
```
