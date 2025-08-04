---
title: Java
short-description: Compiling Java programs
---

# Compiling Java applications

Meson has experimental support for compiling Java programs. The basic syntax consists of only one function and would be used like this:

```meson
project('javaprog', 'java')

myjar = jar('mything', 'com/example/Prog.java',
            main_class : 'com.example.Prog')

test('javatest', myjar)
````

However, note that Meson places some limitations on how you lay out your code:

* All Java files for a JAR must be located under the subdirectory where the JAR definition is declared.
* All Java files must follow the directory path corresponding to their package name. For example, a class called `com.example.Something` must reside in a file located at `com/example/Something.java`.
* Meson only supports building `.jar` files; it does not directly handle individual `.class` files unless done manually.

# Generating native headers for JNI

Since Meson **0.60.0**, a dedicated **Java module** has been added to support advanced Java-native workflows, including generating native headers for Java Native Interface (JNI) development. This eliminates the need to manually create header generation rules with `custom_target()`.

To use the module, first import it:

```meson
jmod = import('java')
```

Then generate JNI headers like this:

```meson
native_header = jmod.generate_native_header('File.java', package: 'com.mesonbuild')
native_header_includes = include_directories('.')
```

These generated headers can be included in native code and compiled into shared libraries or modules. For example:

```meson
jdkjava = shared_module(
  'jdkjava',
  [native_header_includes, other_sources],
  dependencies : [jdk],
  include_directories : [native_header_includes]
)
```

This feature streamlines JNI-based development by automating header generation and integrating it cleanly into the Meson build process.
