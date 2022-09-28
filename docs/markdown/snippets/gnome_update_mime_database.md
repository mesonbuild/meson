## Added `update_mime_database` to `gnome.post_install()`

Applications that install a `.xml` file containing a `mime-type` need to update
the cache upon installation. Most applications do that using a custom script,
but it can now be done by Meson directly.
