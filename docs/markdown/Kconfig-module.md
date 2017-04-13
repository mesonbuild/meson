---
short-description: Unstable kconfig module
authors:
    - name: Mark Schulte, Paolo Bonzini
      years: [2017, 2019]
      has-copyright: false
...

# Unstable kconfig module

This module parses Kconfig output files to allow use of kconfig
configurations in meson projects.

**Note**: this does not provide kconfig frontend tooling to generate a
configuration. You still need something such as kconfig frontends (see
link below) to parse your Kconfig files, and then (after you've
choosen the configuration options), output a ".config" file.

  [kconfig-frontends]: http://ymorin.is-a-geek.org/projects/kconfig-frontends

## Usage

The module may be imported as follows:

``` meson
kconfig = import('unstable-kconfig')
```

The following functions will then be available as methods on the object
with the name `kconfig`. You can, of course, replace the name
`kconfig` with anything else.

### kconfig.load()

This function loads a kconfig output file and returns a dictionary object.

`kconfig.load()` makes no attempt at parsing the values in the
file.  Therefore, true boolean values will be represented as the string "y"
and integer values will have to be converted with `.to_int()`.

* The first (and only) argument is the path to the configuration file to
  load (usually ".config").

**Returns**: a [dictionary object](Reference-manual.md#dictionary-object).
