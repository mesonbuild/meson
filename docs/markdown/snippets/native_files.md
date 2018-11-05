## Native config files

Native files are the counterpart to cross files, and allow specifying
information about the build machine, both when cross compiling and when not.

Currently the native files only allow specifying the names of binaries, similar
to the cross file, for example:

```ini
[binaries]
llvm-config = "/opt/llvm-custom/bin/llvm-config"
```

Will override the llvm-config used for *native* binaries. Targets for the host
machine will continue to use the cross file.
