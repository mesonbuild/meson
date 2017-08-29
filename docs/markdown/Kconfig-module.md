# Kconfig module

This module parser Kconfig output files to allow use of kconfig
configurations in meson projects.

**Note**: this does not provide kconfig frontend tooling to generate a
configuration. You still need something such as kconfig frontends (see
link below) to parse your Kconfig files, and then (after you've
choosen the configuration options), output a ".config" file.

  [kconfig-frontends]: http://ymorin.is-a-geek.org/projects/kconfig-frontends

## Usage

To use this module, just do: **`kconfig = import('kconfig')`**. The
following functions will then be available as methods on the object
with the name `kconfig`. You can, of course, replace the name
`kconfig` with anything else.

### kconfig.load()

This function loads an output file, usually ".config", (the file path
must be specified as the first and only argument) to be used as a
database of configurations. Later functions will operate on this list
of configurations.

* The first (and only) argument is the path to the ".config" file to
  load.

Returns void

### kconfig.is\_set()

After an output file has been loaded, is\_set can be used to check is
a value is defined in the config. This is equivalent to using ifdef
with Makefile or GCC.

* The first (and only) argument is the value for which you want to
  if a config is set. Typically: CONFIG\_FOO.

### kconfig.value()

After an output file has been loaded, value is used to get the actual
value from the output file. An exception is raised if that value does
not exist in the output file.


* The first (and only) argument is the value for which you want to
  if a config is set. Typically: CONFIG\_FOO.
