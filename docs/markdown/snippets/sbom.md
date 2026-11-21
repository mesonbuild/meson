## SBOM generation

`meson setup --sbom` now writes a [protobom](https://github.com/protobom/protobom)
SBOM of the configured project to `<builddir>/sbom.protobom.bin`. The document
lists every configured target and its resolved dependencies, with a
`pkg:generic/<name>@<version>` purl where the project version is known.

The SBOM is generated at configure time, so it contains no artifact hashes.
Meson does not model a supplier or a per-target license, so those fields are
omitted. The output is deterministic when `SOURCE_DATE_EPOCH` is set.
