## Environment Variables with Cross Builds

Previously in Meson, variables like `CC` effected both the host and build
platforms for native builds, but the just the build platform for cross builds.
Now `CC_FOR_BUILD` is used for the build platform in cross builds.

This old behavior is inconsistent with the way Autotools works, which
undermines the purpose of distro-integration that is the only reason
environment variables are supported at all in Meson. The new behavior is not
quite the same, but doesn't conflict: meson doesn't always repond to an
environment when Autoconf would, but when it does it interprets it as Autotools
would.
