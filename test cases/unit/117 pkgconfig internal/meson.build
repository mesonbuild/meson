project('pkgconfig internal', 'c')

pkg = import('pkgconfig')

public_lib = shared_library('public', 'public.c')
private_lib = shared_library('private', 'private.c')
internal_lib = shared_library('internal', 'internal.c')
internal2_lib = shared_library('internal2', 'internal2.c')
main_lib = shared_library('foo', 'foo.c', link_with : [public_lib, private_lib, internal_lib, internal2_lib])

private_dep = declare_dependency(compile_args: '-DPRIVATE')

# What we test here:
# - Even when using shared_library(), when internal: true, we generate
#   private/internal fields. This is more correct because cflags from
#   Requires.private are supposed to be used even for shared libraries.
# - internal_lib is placed into Requires.internal. That's the default place for
#   dependencies.
# - internal2_lib has no pc file, it is thus placed in Libs.private, there is
#   no Libs.internal because it would be identical behaviour as Libs.private.
# - private_lib is promoted to Requires.private.
# - public_lib is promoted to Requires.
# - We can add extra Requires.internal fields.
# - compile_args from private dependencies are added into Cflags field.

pkg.generate(public_lib)
pkg.generate(private_lib)
pkg.generate(internal_lib)
pkg.generate(main_lib,
  libraries: public_lib,
  libraries_private: [private_lib, private_dep],
  requires_internal: 'something',
  internal: true,
)
