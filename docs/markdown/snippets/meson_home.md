## New environment variable `MESON_PACKAGE_CACHE_DIR`

If the `MESON_PACKAGE_CACHE_DIR` environment variable is set, it is used instead of the
project's `subprojects/packagecache`. This allows sharing the cache across multiple
projects. In addition it can contain an already extracted source tree as long as it
has the same directory name as the `directory` field in the wrap file. In that
case, the directory will be copied into `subprojects/` before applying patches.
