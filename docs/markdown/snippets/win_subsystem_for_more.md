## Added `win_subsystem` to `shared_library()` and `shared_module()`

Synonym for the one found in `executable()`.

Mostly useful for setting the subsystem version in PE headers.
This can affects Windows's ShimEngine, but not SxS lookups. Usually you still
want to provide a manifest when targeting modern Windows.
Sometime also useful for targeting other subsystems.

Visual Studio backends now also properly supports setting subsystem versions.
