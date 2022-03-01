## JAR Resources

The ability to add resources to a JAR has been added. Use the `java_resources`
keyword argument. It takes a `sturctured_src` object.

```meson
jar(
  meson.project_name(),
  sources,
  main_class: 'com.mesonbuild.Resources',
  java_resources: structured_sources(
    files('resources/resource1.txt'),
    {
      'subdir': files('resources/subdir/resource2.txt'),
    }
  )
)
```

To access these resources in your Java application:

```java
try (InputStreamReader reader = new InputStreamReader(
        Resources.class.getResourceAsStream("/resource1.txt"),
        StandardCharsets.UTF_8)) {
    // ...
}

try (InputStreamReader reader = new InputStreamReader(
        Resources.class.getResourceAsStream("/subdir/resource2.txt"),
        StandardCharsets.UTF_8)) {
    // ...
}
```
