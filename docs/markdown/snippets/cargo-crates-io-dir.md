## New option `rust.crates_io_dir`

This option can be used to redirect `https://crates.io/` to a local
directory in the filesystem, in which pre-extracted crates are found.
For example, `-Drust.crates_io_dir=/usr/share/cargo/registry` is
equivalent to the following Cargo configuration:

```
[source.local-registry]
directory = "/usr/share/cargo/registry"

[source.crates-io]
registry = "https://crates.io"
replace-with = "local-registry"
```
