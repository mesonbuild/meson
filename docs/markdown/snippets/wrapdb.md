## Automatic fallback using WrapDB

A new command has been added: `meson wrap update-db`. It downloads the list of
wraps available in [WrapDB](wrapdb.mesonbuild.com) and stores it locally in
`subprojects/wrapdb.json`. When that file exists and a dependency is not found
on the system but is available in WrapDB, Meson will automatically download it.
