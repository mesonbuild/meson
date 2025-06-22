## `clang-tidy`'s auto-generated targets correctly select source files

In previous versions, the target would run `clang-tidy` on _every_ C-like source files (.c, .h, .cpp, .hpp). It did not work correctly because some files, especially headers, are not intended to be consumed as is.

It will now run only on source files participating in targets.
