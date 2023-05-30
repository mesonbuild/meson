## Unified message(), str.format() and f-string formatting

They now all support the same set of values: strings, integers, bools, options,
dictionaries and lists thereof.

- Feature options (i.e. enabled, disabled, auto) were not previously supported
  by any of those functions.
- Lists and dictionaries were not previously supported by f-string.
- str.format() allowed any type and often resulted in printing the internal
  representation which is now deprecated.
