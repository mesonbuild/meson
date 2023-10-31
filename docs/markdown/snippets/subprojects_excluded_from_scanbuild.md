## Subprojects excluded from scan-build reports

The `scan-build` target, created when using the `ninja` backend with `scan-build`
present, now excludes bugs found in subprojects from its final report.
