## MSVC compiler now assumes UTF-8 source code by default

Every project that uses UTF-8 source files had to add manually `/utf-8` C/C++
compiler argument for MSVC otherwise they wouldn't work on non-English locale.
Meson now switched the default to UTF-8 to be more consistent with all other
compilers.

This can be overridden but using `/source-charset`:
```meson
if cc.get_id() == 'msvc'
  add_project_arguments('/source-charset:.XYZ', language: ['c', 'cpp'])
endif
```

See Microsoft documentation for details:
https://docs.microsoft.com/en-us/cpp/build/reference/source-charset-set-source-character-set.
