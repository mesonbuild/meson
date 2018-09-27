# Meson Documentation

## Build dependencies

Meson uses itself and [hotdoc](https://github.com/hotdoc/hotdoc) for generating documentation.

Minimum required version of hotdoc is *0.8.9*.

Instructions on how to install hotdoc are [here](https://hotdoc.github.io/installing.html).

## Building the documentation

From the Meson repository root dir:
```
$ cd docs/
$ meson built_docs
$ ninja -C built_docs/ upload
```
Now you should be able to open the documentation locally
```
built_docs/Meson documentation-doc/html/index.html
```

## Upload

Meson uses the git-upload hotdoc plugin which basically
removes the html pages and replaces with the new content.

You can simply run:
```
$ ninja -C built_docs/ upload
```

## Contributing to the documentation

Commits that only change documentation should have `[skip ci]` in their commit message, so CI is not run (it is quite slow).
For example:
```
A commit message [skip ci]
```
