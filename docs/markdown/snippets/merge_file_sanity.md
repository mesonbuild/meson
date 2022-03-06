## i18n.merge_file no longer arbitrarily leaves your project half-built

The i18n module partially accounts for builds with NLS disabled, by disabling
gettext compiled translation catalogs if it cannot build them. Due to
implementation details, this also disabled important data files created via
merge_file, leading to important desktop files etc. not being installed.

This overreaction has been fixed. It is no longer possible to have NLS-disabled
builds which break the project by not installing important files which have
nothing to do with NLS (other than including some).

If you were depending on not having the Gettext tools installed and
successfully mis-building your project, you may need to make your project
actually work with NLS disabled, for example by providing some version of your
files which is still installed even when merge_file cannot be run.
