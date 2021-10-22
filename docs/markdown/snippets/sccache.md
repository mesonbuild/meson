## Added support for sccache

Meson now supports [sccache](https://github.com/mozilla/sccache) just
like it has supported CCache. If both sccache and CCache are
available, the autodetection logic prefers sccache.
