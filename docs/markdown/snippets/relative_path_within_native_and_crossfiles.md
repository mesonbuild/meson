## Relative paths are supported within native and cross files

The binaries specified in the machine file can now be defined
by using their relative path in relation to the machine file
If the following machine file is located under 
`/my_project/toolchain` the entry for `c` will be extended 
to `/my_project/toolchain/bin/gcc`.

```ini
c = 'bin/gcc'
```
