## Gettext targets are ignored if `gettext` is not installed

Previously the `i18n` module has errored out when `gettext` tools are
not installed on the system. Starting with this version they will
become no-ops instead. This makes it easier to build projects on
minimal environments (such as when bootstrapping) that do not have
translation tools installed.
