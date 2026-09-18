## Added support for buildcache

Meson now recognizes [BuildCache](https://gitlab.com/bits-n-bites/buildcache)
as a compiler wrapper, so setting e.g. `CC="buildcache cc"` works like it
already does for Ccache and sccache. BuildCache is also auto-detected
alongside Ccache and sccache, and is used as a fallback after both of those
when no compiler is specified explicitly.