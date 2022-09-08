## Run gtk-update-icon-cache in custom directories

The `gtk_update_icon_cache` keyword argument of `gnome.post_install()` now accepts
a list of directories relative to `prefix` where the icon cache will be updated.

```meson
gnome.post_install(
    gtk_update_icon_cache: get_option('datadir') / meson.project_name() / 'icons' / 'hicolor'
)
```
