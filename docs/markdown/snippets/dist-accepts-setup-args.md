## dist now accepts arguments to be passed to setup

When performing a distcheck, it is sometimes desirable to check various
configurations. Previously, Meson ran the distcheck using the same
configuration as the current build. Now it is possible to override this in
`meson dist` without first reconfiguring the main build.
