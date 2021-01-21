## JDK System Dependency

When building projects such as those interacting with the JNI, you need access
to a few header files located in `JAVA_HOME`. This system dependency will add
the correct include paths to your target assuming the dependency has been setup
properly with `JAVA_HOME` pointing to a valid JDK installation.

```meson
jdk = dependency('jdk', version : '>=1.8', required : true)
```

Currently this system dependency only works on linux, win32, and darwin. This
can easily be extended given the correct information about your compiler and
platform.
