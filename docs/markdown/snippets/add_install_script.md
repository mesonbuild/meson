## `meson.add_install.script()` accepts CustomTarget as first argument

It was previously wrongly documented as supported, but now CustomTarget and
CustomTarget indexes are supported. It was already accepted in script arguments
before.
