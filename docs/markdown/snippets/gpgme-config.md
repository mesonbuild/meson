## gpgme dependency now supports gpgme-config

Previously, we could only detect GPGME with custom invocations of `gpgme-config`. Now we added support to Meson allowing us to use `dependency('gpgme')` instead.
