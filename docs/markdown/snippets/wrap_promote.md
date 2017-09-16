# Can promote dependencies with wrap command

The `promote` command makes it easy to copy nested dependencies to the top level.

    meson wrap promote scommon

This will search the project tree for a subproject called `scommon` and copy it to the top level.

If there are many embedded subprojects with the same name, you have to specify which one to promote manually like this:

    meson wrap promote subprojects/s1/subprojects/scommon
