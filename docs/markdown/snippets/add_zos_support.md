## Support for z/OS

z/OS is now supported with the Open XL C/C++ for z/OS compiler. Data
set inputs and outputs are not directly supported by Meson.

Shared libraries with a name that is valid as a PDSE member will not
have a prefix or suffix implicitly added. This allows the shared
library to be installed to a PDSE library and found through the
standard system search order.
