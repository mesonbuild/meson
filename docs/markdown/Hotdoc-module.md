---
short-description: Hotdoc module
authors:
    - name: Thibault Saunier
      email: tsaunier@igalia.com
      years: [2018]
      has-copyright: false
...

# Hotdoc module

This module provides helper functions for generating documentation using
[hotdoc].

*Added 0.48.0*

## Usage

To use this module, just do: **`hotdoc = import('hotdoc')`**. The
following functions will then be available as methods on the object
with the name `hotdoc`. You can, of course, replace the name `hotdoc`
with anything else.

### hotdoc.generate_doc()

Generates documentation using [hotdoc] and installs it into `$prefix/share/doc/html`.

**Positional argument:**

* `project_name`: The name of the hotdoc project

**Keyworded arguments:**

* `sitemap` (*[string] or [file]*) (**required**): The hotdoc sitemap file
* `index` (*[string] or [file]*) (**required**): Location of the index file
* `dependencies`(*[targets]*): Targets on which the documentation generation depends on.
* `subprojects`: A list of `HotdocTarget` that are used as subprojects for hotdoc to generate
  the documentation.
* ... Any argument of `hotdoc` can be used replacing dashes (`-`) with underscores (`_`).
  For a full list of available parameters, just have a look at `hotdoc help`.

[file]: Reference-manual.md#files
[string]: Reference-manual.md#string-object
[targets]: Reference-manual.md#build-target-object

**Returns:**

`HotdocTarget`: A [`custom_target`](Reference-manual.md#custom-target-object) with the
following extra methods:

* `config_path`: Path to the generated `hotdoc` configuration file.

### hotdoc.has_extensions()

**Positional arguments:**

* `...`: The hotdoc extension names to look for

**No keyworded arguments**

**Returns:** `true` if all the extensions where found, `false` otherwise.

### Example

``` meson
hotdoc = import('hotdoc')

hotdoc.generate_doc('foobar',
  project_version: '0.1',
  sitemap: 'sitemap.txt',
  index: 'index.md',
  c_sources: ['path/to/file.c'],
  c_smart_index: true,
  languages: ['c'],
  install: true,
)
```

[hotdoc]: https://hotdoc.github.io/