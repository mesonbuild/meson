## gpgme dependency now supports gpgme-config

Previously, we could only detect GPGME with custom invocations of `gpgme-config` or when the GPGME version was recent enough (>=1.13.0) to install pkg-config files. Now we added support to Meson allowing us to use `dependency('gpgme')` and fall back on `gpgme-config` parsing.
