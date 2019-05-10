## Support for the Intel Compiler on Windows (ICL)

Support has been added for ICL.EXE and ifort on windows. The support should be
on part with ICC support on Linux/MacOS. The ICL C/C++ compiler behaves like
Microsoft's CL.EXE rather than GCC/Clang like ICC does, and has a different id,
`intel-cl` to differentiate it.

```meson
cc = meson.get_compiler('c')
if cc.get_id == 'intel-cl'
  add_project_argument('/Qfoobar:yes', language : 'c')
endif
```
