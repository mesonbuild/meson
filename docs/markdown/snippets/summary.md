## Add a new summary() function

A new function [`summary()`](Reference-manual.md#summary) has been added to
summarize build configuration at the end of the build process.

Example:
```meson
project('My Project', version : '1.0')
summary('Directories', {'bindir': get_option('bindir'),
                        'libdir': get_option('libdir'),
                        'datadir': get_option('datadir'),
                        })
summary('Configuration', {'Some boolean': false,
                          'Another boolean': true,
                          'Some string': 'Hello World',
                          'A list': ['string', 1, true],
                          })
```

Output:
```
My Project 1.0

  Directories
             prefix: /opt/gnome
             bindir: bin
             libdir: lib/x86_64-linux-gnu
            datadir: share

  Configuration
       Some boolean: False
    Another boolean: True
        Some string: Hello World
             A list: string
                     1
                     True
```
