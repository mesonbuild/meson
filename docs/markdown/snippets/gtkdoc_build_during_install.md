## gnome.gtkdoc new option `build_during_build` can build during build

`gnome.gtkdoc` has had a long outstanding bug where gtk documentation was
not build during `meson compile` but during `meson install`, leading to a
wide set of errors. However, simply forcing the gtk documentation to be
built during `meson compile` is likely going to disrupt many meson users, due
to the long times required to build gtk documentation. This is unfortunate,
as users should not rely on meson bugs to simplify their work (in this case,
reduce build time by skipping documentation builds). The right way for users
to do this is to create a `gtk_doc` boolean meson option which conditionally
enables building the documentation:

```meson
gnome = import('gnome', required : get_option('gtk_doc'), disabler : true)
gnome.gtkdoc(...)
```

Or in case building the documentation compromises more than just running
`gnome.gtkdoc`:

```meson
gnome = import('gnome')

if get_option('gtk_doc')
  gnome.gtkdoc(...)
  custom_target(...)
endif
```

In consequence, to directly avoid disrupting these users, but start moving
in the right direction, the transition process will be the following:
 * In current release, add boolean `build_during_build` with `False` as default
   to `gnome.gtkdoc` and add a warning. This should not disrupt current users
   of `gtk_doc`-like options, while warning users that are relying in the bug.
 * In a future meson release, change `build_during_build` default to `True`
   and deprecate it. This might break those users that have not done the
   transition, but given there was enough time and notice, it should not be an
   issue.
 * In a further meson release, remove `build_during_build` option and warranty
   that gtk documentation is always build during `meson compile` step.
