# I18n module

This module provides internationalisation and localisation functionality.

## Usage

To use this module, just do: **`i18n = import('i18n')`**. The following functions will then be available as methods on the object with the name `i18n`. You can, of course, replace the name `i18n` with anything else.

### i18n.gettext()

Sets up gettext localisation so that translations are built and placed into their proper locations during install. Takes one positional argument which is the name of the gettext module.

* `languages`: list of languages that are to be generated. As of 0.37.0 this is optional and the [LINGUAS](https://www.gnu.org/software/gettext/manual/html_node/po_002fLINGUAS.html) file is read.
* `data_dirs`: (*Added 0.36.0*) list of directories to be set for `GETTEXTDATADIRS` env var (Requires gettext 0.19.8+), used for local its files
* `preset`: (*Added 0.37.0*) name of a preset list of keywords, flags and arguments, current option is `'glib'`, see [source](https://github.com/mesonbuild/meson/blob/master/mesonbuild/modules/i18n.py) for their value
* `args`: list of extra arguments to pass to `xgettext` when generating the pot file

This function also defines targets for maintainers to use:
**Note**: These output to the source directory

* `<project_id>-pot`: runs `xgettext` to regenerate the pot file
* `<project_id>-update-po`: regenerates the `.po` files from current `.pot` file
* `<project_id>-gmo`: builds the translations without installing

### i18n.merge_file()

This merges translations into a text file using `msgfmt`. See [custom_target](https://github.com/mesonbuild/meson/wiki/Reference%20manual#custom_target) for normal keywords. In addition it accepts these keywords:

* `po_dir`: directory containing translations, relative to current directory
* `data_dirs`: (*Added 0.41.0*) list of directories for its files (See also `i18n.gettext()`)
* `type`: type of file, valid options are `'xml'` (default) and `'desktop'`

*Added 0.37.0*

### i18n.files()

```meson
  i18n.files(*file1*, *file2*, ...)
```

*Added 0.42.0*

This function is a wrapper for `files()`. It carries additional metadata to allow string extraction and translation merging.
These are all the supported keyword arguments:

* `language`: the (computer) language of the files
* `keywords`: list of keywords used to extract strings (use the special `''` value to disable default keywords)
* `flags`: list of flags used to extract strings
* `extra_args`: list of extra arguments to pass to `xgettext`
* `preset`: name of a preset list of keywords, flags and arguments (see `i18n.create_pot()`)

If `language` is either `'xml'` or `'desktop'`, these additional keyword arguments are allowed:

* `merge`: whether to merge the translations or not (if `false`, the following arguments are unused)
* `suffix`: this suffix will be stripped from file names to get the output file name and target name
* Keyword arguments from `custom_target`, except: `input`, `output`, `capture`, `command`, `depfile`.

### i18n.create_pot()

```meson
  i18n.create_pot(*name*, *i18n_files1*, *i18n_files2*, ...)
```

*Added 0.42.0*

Sets up gettext localisation so that translations are built and placed into their proper locations during install.
It has the same effect as `i18n.gettext()`, except the files are passed explicitly and thus can have per-files extra arguments, keywords and flags.

These are all the supported keyword arguments:

* `languages`: list of languages that are to be generated. As of 0.37.0 this is optional and the [LINGUAS](https://www.gnu.org/software/gettext/manual/html_node/po_002fLINGUAS.html) file is read.
* `data_dirs`: list of directories to be set for `GETTEXTDATADIRS` env var (Requires gettext 0.19.8+), used for local its files
* `preset`: name of a preset list of keywords, flags and arguments, current option is `'glib'`, see [source](https://github.com/mesonbuild/meson/blob/master/mesonbuild/modules/i18n.py) for their value

This function also defines targets for maintainers to use:
**Note**: These output to the source directory

* `<project_id>-pot`: runs `xgettext` to regenerate the pot file
* `<project_id>-update-po`: regenerates the `.po` files from current `.pot` file
* `<project_id>-gmo`: builds the translations without installing

You can get the list of `custom_target()` objects created for each file to merge using `i18n_pot.get_custom_targets()`.
