## JNI System Dependency Modules

The JNI system dependency now supports a `modules` keyword argument which is a
list containing any of the following: `jvm`, `awt`.

```meson
jni_dep = dependency('jni', version: '>= 1.8.0', modules: ['jvm', 'awt'])
```

This will add appropriate linker arguments to your target.
