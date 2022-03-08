## New custom dependency for OpenSSL

Detecting an OpenSSL installation in a cross-platform manner can be
complicated. Officially, pkg-config is supported by upstream. Unofficially,
cmake includes a FindOpenSSL using a different name and which requires
specifying modules.

Meson will now allow the pkg-config name to work in all cases using the following lookup order:
- prefer pkg-config if at all possible
- attempt to probe the system for the standard library naming, and retrieve the version from the headers
- if all else fails, check if cmake can find it
