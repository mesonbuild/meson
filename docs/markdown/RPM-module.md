# RPM module

The RPM module can be used to create a sample rpm spec file for a
Meson project. It autodetects installed files, dependencies and so
on. Using it is very simple. At the very end of your Meson project
(that is, the end of your top level `meson.build` file) add these two
lines.

```meson
rpm = import('rpm')
rpm.generate_spec_template()
```

Run Meson once on your code and the template will be written in your
build directory. Then remove the two lines above and manually edit the
template to add missing information. After this it is ready for use.
