# Can index CustomTaget objects

The `CustomTarget` object can now be indexed like an array. The resulting
object can be used as a source file for other Targets, this will create a
dependency on the original `CustomTarget`, but will only insert the generated
file corresponding to the index value of the `CustomTarget`'s `output` keyword.

    c = CustomTarget(
      ...
      output : ['out.h', 'out.c'],
    )
    lib1 = static_library(
      'lib1',
      [lib1_sources, c[0]],
      ...
    )
    exec = executable(
      'executable',
      c[1],
      link_with : lib1,
    )
