## Added devenv to introspection data

Introspection data now contains environment variables defined in devenv.

This allows external tools to use that information to launch executables
from the build directory without the need to call `meson devenv`.

As a side effect, it also mades it possible to dump `devenv` in `json` format,
using `meson introspect --devenv`.
