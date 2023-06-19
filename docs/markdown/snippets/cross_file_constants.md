## Cross and native file constants

The value in `[constants]` section of cross and native files can now be overridden
using `--cross-file-constant name=value` and `--native-file-constant name=value`
command line arguments. Constants that don't have a default value must still be
declared in the `[constants]` section with no value, user will have to set their
value on the command line. This is intended to be used for example to set the path
where user installed the toolchain or SDK. In the example below, user must pass
`--cross-file-constant pkgconf=<value>` in the command line, and can pass
`--cross-file-constant somepath=/other/path/to/toolchain` if they installed the
toolchain in another location than the default.

```ini
[constants]
pkgconf =
somepath = '/default/path/to/toolchain'
[binaries]
c = somepath / 'gcc'
cpp = somepath / 'g++'
pkgconfig = pkgconf
```
