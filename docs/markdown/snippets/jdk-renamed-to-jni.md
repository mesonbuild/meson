## JDK System Dependency Renamed from `jdk` to `jni`

The JDK system dependency is useful for creating native Java modules using the
JNI. Since the purpose is to find the JNI, it has been decided that a better
name is in fact "jni". Use of `dependency('jdk')` should be replaced with
`dependency('jni')`.
