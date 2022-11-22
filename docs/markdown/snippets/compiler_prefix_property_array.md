## Compiler check functions `prefix` kwargs accepts arrays

The `prefix` kwarg that most compiler check functions support
now accepts an array in addition to a string. The elements of the
array will be concatenated separated by a newline.

This makes it more readable to write checks that need multiple headers
to be included:

```meson
cc.check_header('GL/wglew.h', prefix : ['#include <windows.h>', '#include <GL/glew.h>'])
```

instead of

```meson
cc.check_header('GL/wglew.h', prefix : '#include <windows.h>\n#include <GL/glew.h>'])
```
