## Added support for IBM i

Meson now recognizes IBM i (also known as OS/400) when it is running
in the PASE environment.  `host_machine.system()` returns `'aix'`
because the user space is the same as AIX, but  `host_machine.kernel()`
returns `'os400'` to tell the two systems apart.
