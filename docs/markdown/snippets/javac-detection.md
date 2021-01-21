## Java Compiler Detection

The way that Meson detects `javac` has changed a little bit. Meson will now
read the `JAVA_HOME` environment variable when looking for `javac` and will
then fallback to looking for `javac` on the `PATH` if `JAVA_HOME` was unset.
