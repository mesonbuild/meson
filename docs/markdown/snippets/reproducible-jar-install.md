## Jar files are now installed reproducibly

Installing a jar target used to invoke the `jar` tool to strip the
`Class-Path` attribute from its manifest, even when there was none.
This replaced the manifest's timestamp inside the jar with the time of
installation, so two builds of the same sources produced different
installed jars.

Manifests are now edited with Python's `zipfile` module instead. Jars
without a `Class-Path` attribute are installed unmodified, and when the
attribute has to be stripped, all entry metadata such as timestamps is
preserved. As a side effect, the `jar` binary is no longer needed at
install time.
