# Config-Tool based dependencies can be specified in a cross file

Tools like LLVM and pcap use a config tool for dependencies, this is a script
or binary that is run to get configuration information (cflags, ldflags, etc)
from.

These binaries may now be specified in the `binaries` section of a cross file.

```dosini
[binaries]
cc = ...
llvm-config = '/usr/bin/llvm-config32'
```
