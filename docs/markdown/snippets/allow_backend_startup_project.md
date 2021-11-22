## Allow backend_startup_project with all backends

`backend_startup_project` will be ignored with non-VS backends and as such safe
to use in a project's options in `meson.build`.
