## Deprecated `java.generate_native_header()` in favor of the new `java.generate_native_headers()`

`java.generate_native_header()` was only useful for the most basic of
situations. It didn't take into account that in order to generate native
headers, you had to have all the referenced Java files. It also didn't take
into account inner classes. Do not use this function from `0.62.0` onward.

`java.generate_native_headers()` has been added as a replacement which should account for the previous function's shortcomings.

```java
// Outer.java

package com.mesonbuild;

public class Outer {
    private static native void outer();

    public static class Inner {
        private static native void inner();
    }
}
```

With the above file, an invocation would look like the following:

```meson
java = import('java')

native_headers = java.generate_native_headers(
    'Outer.java',
    package: 'com.mesonbuild',
    classes: ['Outer', 'Outer.Inner']
)
```
