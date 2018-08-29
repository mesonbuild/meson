## Hotdoc module

A new module has been written to ease generation of [hotdoc](https://hotdoc.github.io/) based
documentation. It supports complex use cases such as hotdoc subprojects (to create documentation
portals) and makes it straight forward to leverage full capabilities of hotdoc.

Simple usage:

``` meson
hotdoc = import('hotdoc')

hotdoc.generate_doc(
  'foobar',
  c_smart_index: true,
  project_version: '0.1',
  sitemap: 'sitemap.txt',
  index: 'index.md',
  c_sources: ['path/to/file.c'],
  languages: ['c'],
  install: true,
)
```