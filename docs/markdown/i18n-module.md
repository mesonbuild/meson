# I18n module

This module provides internationalisation and localisation functionality.

## Usage

To use this module, just do: **`i18n = import('i18n')`**. The
following functions will then be available as methods on the object
with the name `i18n`. You can, of course, replace the name `i18n` with
anything else.

### i18n.gettext()

Sets up gettext localisation so that translations are built and placed
into their proper locations during install. Takes one positional
argument which is the name of the gettext module.

* `args`: list of extra arguments to pass to `xgettext` when
  generating the pot file
* `data_dirs`: (*Added 0.36.0*) list of directories to be set for
  `GETTEXTDATADIRS` env var (Requires gettext 0.19.8+), used for local
  its files
* `languages`: list of languages that are to be generated. As of
  0.37.0 this is optional and the
  [LINGUAS](https://www.gnu.org/software/gettext/manual/html_node/po_002fLINGUAS.html)
  file is read.
* `preset`: (*Added 0.37.0*) name of a preset list of arguments,
  current option is `'glib'`, see
  [source](https://github.com/mesonbuild/meson/blob/master/mesonbuild/modules/i18n.py)
  for their value
* `install`: (*Added 0.43.0*) if false, do not install the built translations.
* `install_dir`: (*Added 0.50.0*) override default install location, default is `localedir`

This function also defines targets for maintainers to use:
**Note**: These output to the source directory

* `<project_id>-pot`: runs `xgettext` to regenerate the pot file
* `<project_id>-update-po`: regenerates the `.po` files from current `.pot` file
* `<project_id>-gmo`: builds the translations without installing

(*since 0.60.0*) Returns a list containing:
* a list of built `.mo` files
* the maintainer `-pot` target
* the maintainer `-update-po` target

### i18n.merge_file()

This merges translations into a text file using `msgfmt`. See
[[custom_target]]
for normal keywords. In addition it accepts these keywords:

* `output`: same as `custom_target` but only accepts one item
* `install_dir`: same as `custom_target` but only accepts one item
* `install_tag`: same as `custom_target` but only accepts one item
* `data_dirs`: (*Added 0.41.0*) list of directories for its files (See
  also `i18n.gettext()`)
* `po_dir`: directory containing translations, relative to current directory
* `type`: type of file, valid options are `'xml'` (default) and `'desktop'`
* `args`: (*Added 0.51.0*) list of extra arguments to pass to `msgfmt`

*Added 0.37.0*

### i18n.itstool_join()

This joins translations into a XML file using `itstool`. See
[[custom_target]]
for normal keywords. In addition it accepts these keywords:

* `output`: same as `custom_target` but only accepts one item
* `install_dir`: same as `custom_target` but only accepts one item
* `install_tag`: same as `custom_target` but only accepts one item
* `its_files`: filenames of ITS files that should be used explicitly
  (XML translation rules are autodetected otherwise).
* `mo_targets` *required*: mo file generation targets as returned by `i18n.gettext()`.

*Added 0.62.0*


### i18n.xgettext()

``` meson
i18n.xgettext(name, sources..., args: [...], recursive: false)
```

Invokes the `xgettext` program on given sources, to generate a `.pot` file.
This function is to be used when the `gettext` function workflow it not suitable
for your project. For example, it can be used to produce separate `.pot` files
for each executable.

Positional arguments are the following:

* name `str`: the name of the resulting pot file.
* sources `array[str|File|build_tgt|custom_tgt]`:
          source files or targets. May be a list of `string`, `File`, [[@build_tgt]],
          or [[@custom_tgt]] returned from other calls to this function.

Keyword arguments are the following:

- recursive `bool`:
        if `true`, will merge the resulting pot file with extracted pot files
        related to dependencies of the given source targets. For instance,
        if you build an executable, then you may want to merge the executable
        translations with the translations from the dependent libraries.
- install `bool`: if `true`, will add the resulting pot file to install targets.
- install_tag `str`: install tag to use for the install target.
- install_dir `str`: directory where to install the resulting pot file.

The `i18n.xgettext()` function returns a [[@custom_tgt]].

Usually, you want to pass one build target as sources, and the list of header files
for that target. If the number of source files would result in a command line that
is too long, the list of source files is written to a file at config time, to be
used as input for the `xgettext` program.

The `recursive: true` argument is to be given to targets that will actually read
the resulting `.mo` file. Each time you call the `i18n.xgettext()` function,
it maps the source targets to the resulting pot file. When `recursive: true` is
given, all generated pot files from dependencies of the source targets are
included to generate the final pot file. Therefore, adding a dependency to
source target will automatically add the translations of that dependency to the
needed translations for that source target.

*Added 1.8.0*
