## Can link against custom targets

The output of `custom_target` can be used in `link_with` and
`link_whole` keyword arguments. This is useful for integrating custom
code generator steps, but note that there are many limitations:

 - Meson can not know about link dependencies of the custom target. If
   the target requires further link libraries, you need to add them manually

 - The user is responsible for ensuring that the code produced by
   different toolchains are compatible.

 - The custom target can only have one output file.

 - The output file must have the correct file name extension.

