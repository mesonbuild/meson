## Cross and native file constants

Constants can be defined in the `[constants]` section and used in other
sections as `@varname@`. See [here](Cross-compilation.md#constants)
for details.

```ini
[constants]
somepath = '/path/to/toolchain'
[binaries]
c = '@somepath@/gcc'
cpp = '@somepath@/g++'
```
