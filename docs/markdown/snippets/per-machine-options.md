## Specifying options per mer machine

Previously, no cross builds were controllable from the command line.
Machine-specific options like the pkg-config path and compiler options only
affected native targets, that is to say all targets in native builds, and
`native: true` targets in cross builds. Now, prefix the option with `build.` to
affect build machine targets, and leave it unprefixed to affect host machine
targets.

For those trying to ensure native and cross builds to the same platform produced
the same result, the old way was frustrating because very different invocations
were needed to affect the same targets, if it was possible at all. Now, the same
command line arguments affect the same targets everwhere --- Meson is closer to
ignoring whether the "overall" build is native or cross, and just caring about
whether individual targets are for the build or host machines.
