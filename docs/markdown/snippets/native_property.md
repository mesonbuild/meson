## Native file properties

As of Meson 0.53.0, the `--native-file foo.txt` can contain:

* binaries
* paths
* properties

which are defined and used the same way as in cross files.
The `properties` are new for Meson 0.53.0, and are read like:

```meson
x = meson.get_native_property('foobar', 'foo')
```

where `foobar` is the property name, and the optional `foo` is the fallback string value.