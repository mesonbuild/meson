## Project version can be specified with a file

Meson can be instructed to load project's version string from an
external file like this:

```meson
project('foo', 'c' version: files('VERSION'))
```

The version file must contain exactly one line of text and that will
be set as the project's version. If the line ends in a newline
character, it is removed.
