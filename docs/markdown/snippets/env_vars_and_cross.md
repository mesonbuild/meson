## Environment Variables with Cross Builds

Previously in Meson, variables like `CC` effected both the host and build
platforms for native builds, but the just the build platform for cross builds.
Now `CC` always effects the host platform, and `CC_FOR_BUILD` always affects
the build platform, with `CC` also effecting the build platform for native
builds only when `CC_FOR_BUILD` is not defined.

This old behavior is inconsistent with the way Autotools works, which
undermines the purpose of distro-integration that is the only reason
environment variables are supported at all in Meson. The new behavior is
consistent.
