## Project version can be specified with a file

Meson can be instructed to load a project's version string from an
external file like this:

```meson
project('foo', 'c' version: files('VERSION'))
```

The version file must contain exactly one line of text which will
be used as the project's version. If the line ends in a newline
character, it is removed.
