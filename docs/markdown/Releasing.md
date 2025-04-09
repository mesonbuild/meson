---
short-description: Release Policy
...

# Releasing a new Meson version

For each new meson release, several different artifacts are created:

- Github Releases:
  - canonical source tarball, PGP signed: `packaging/builddist.sh`
  - Windows installer: `packaging/createmsi.py`
  - macOS installer: `packaging/createpkg.py`
- PyPI:
  - pip install-compatible release, as produced by builddist.sh
- Debian package: `packaging/mpackage.py`

# Release team


- Jussi Pakkanen. PGP key: [19E2D6D9B46D8DAA6288F877C24E631BABB1FE70](https://keyserver.ubuntu.com/pks/lookup?search=0x19E2D6D9B46D8DAA6288F877C24E631BABB1FE70&op=index)
- Eli Schwartz. PGP key: [BD27B07A5EF45C2ADAF70E0484818A6819AF4A9B](https://keyserver.ubuntu.com/pks/lookup?search=0xBD27B07A5EF45C2ADAF70E0484818A6819AF4A9B&op=index)
- Dylan Baker. PGP key: [71C4B75620BC75708B4BDB254C95FAAB3EB073EC](https://keyserver.ubuntu.com/pks/lookup?search=0x71C4B75620BC75708B4BDB254C95FAAB3EB073EC&op=index)

The default release manager for new versions of Meson is Jussi Pakkanen. Starting with meson 1.8.0, the release team has been expanded with fallback options to reduce the bus factor, but will continue to be done by Jussi when possible.
