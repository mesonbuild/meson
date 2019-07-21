## Dist is now a top level command

Previously creating a source archive could only be done with `ninja
dist`. Starting with this release Meson provides a top level `dist`
that can be invoked directly. It also has a command line option to
determine which kinds of archives to create:

```meson
meson dist --formats=xztar,zip
```
