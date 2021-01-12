## Buildtype remains even if dependent options are changed

Setting the `buildtype' option to a value sets the `debug` and
`optimization` options to predefined values. Traditionally setting the
options to other values would then change the buildtype to `custom`.
This is confusing and means that you can't use, for example, debug
level `g` in `debug` buildtype even though it would make sense under
many circumstances. Starting with the buildtype is only changed when
the user explicitly sets it. Setting the build type sets the other
options to their default values as before.