## Machine files now expand `~` as the user's home directory

A new constant `~` has been added which can be used in machine files (native
and cross files) to refer to the user's home directory. This is useful for
specifying paths to SDKs and toolchains that are commonly installed into `~`,
such as Qt or the Android SDK/NDK:

```ini
[constants]
toolchain = ~ / 'Android/sdk/ndk/27.1.12297006/toolchains/llvm/prebuilt/linux-x86_64'

[binaries]
c = toolchain / 'bin/clang'
cpp = toolchain / 'bin/clang++'
```
