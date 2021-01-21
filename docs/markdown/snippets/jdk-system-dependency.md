## JDK System Dependency

When building projects such as those interacting with the JNI, you need access
to a few header files located in a Java installation. This system dependency
will add the correct include paths to your target. It assumes that either
`JAVA_HOME` will be set to a valid Java installation, or the default `javac` on
your system is a located in the `bin` directory of a Java installation. Note:
symlinks are resolved.

```meson
jdk = dependency('jdk', version : '>=1.8')
```

Currently this system dependency only works on `linux`, `win32`, and `darwin`.
This can easily be extended given the correct information about your compiler
and platform in an issue.
