## (C) Preprocessor flag handling

Meson previously stored `CPPFLAGS` and per-language compilation flags
separately. (That latter would come from `CFLAGS`, `CXXFLAGS`, etc., along with
`<lang>_args` options whether specified no the command-line interface (`-D..`),
`meson.build` (`default_options`), or cross file (`[properties]`).) This was
mostly unobservable, except for certain preprocessor-only checks like
`check_header` would only use the preprocessor flags, leading to confusion if
some `-isystem` was in `CFLAGS` but not `CPPFLAGS`. Now, they are lumped
together, and `CPPFLAGS`, for the languages which are deemed to care to about,
is just another source of compilation flags along with the others already
listed.
