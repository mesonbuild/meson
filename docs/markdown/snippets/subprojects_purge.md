## Purge subprojects folder

It is now possible to purge a subprojects folder of artifacts created
from wrap-based subprojects including anything in `packagecache`. This is useful
when you want to return to a completely clean source tree or busting caches with
stale patch directories or caches. By default the command will only print out
what it is removing. You need to pass `--confirm` to the command for actual
artifacts to be purged.

By default all wrap-based subprojects will be purged.

- `meson subprojects purge` prints non-cache wrap artifacts which will be
purged.
- `meson subprojects purge --confirm` purges non-cache wrap artifacts.
- `meson subprojects purge --confirm --include-cache` also removes the cache
artifacts.
- `meson subprojects purge --confirm subproj1 subproj2` removes non-cache wrap
artifacts associated with the listed subprojects.
