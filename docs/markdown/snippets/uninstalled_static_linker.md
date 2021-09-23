## More efficient static linking of uninstalled libraries

A somewhat common use case of [[static_library]] is to create uninstalled
internal convenience libraries which are solely meant to be linked to other
targets. Some build systems call these "object libraries". Meson's
implementation does always create a static archive.

This will now check to see if the static linker supports "thin archives"
(archives which do not contain the actual object code, only references to their
location on disk) and if so, use them to minimize space usage and speed up
linking.
