## Machine files now expand `~` as the user's home directory

A new constant `~` has been added which can be used in machine files (native
and cross files) to refer to the user's home directory. This is useful for
specifying paths to SDKs and toolchains that are commonly installed into `~`,
such as Qt, the Android SDK/NDK, or user-installed frameworks on macOS:

```ini
[constants]
toolchain = ~ / 'Android/sdk/ndk/27.1.12297006/toolchains/llvm/prebuilt/linux-x86_64'

[binaries]
c = toolchain / 'bin/clang'
cpp = toolchain / 'bin/clang++'
ar = toolchain / 'bin/llvm-ar'
```

Note that `~` can be used anywhere in the machine file. In the above example,
the purpose of defining a new constant called `toolchain` is to not have to
repeat yourself when using the path multiple times.
