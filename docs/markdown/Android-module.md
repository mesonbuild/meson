# Android module

This module provides mechanisms to build applications on Android.

## Usage

To use this module, just do: **`android = import('android')`**. The
following functions will then be available as methods on the object
with the name `android`. You can, of course, replace the name
`android` with anything else.

### android.generate_apk()

```
    android.generate_apk(manifest: string | File | CustomTarget | CustomTargetIndex | GeneratedList,
                         sources ... : string | File | CustomTarget | CustomTargetIndex | GeneratedList | Jar,
                         app_id: string | None = None,
                         target_sdk: int | None = None,
                         min_sdk: int | None = None,
                         resources: [](string | File | CustomTarget | CustomTargetIndex | GeneratedList) = [],
                         install: bool = false,
                         install_dir: string | None = None,
                         install_tag: string | None = None,
                         ): CustomTarget
```

This function generates an Android APK file based on the manifest and
sources passed to it.

**DO NOT** use this for deploying production applications. The format
this effectivly produces (arch-split APKs) is not accepted by Google
anymore and the new application bundle format is entirely incompatible
with the way meson works. For production applications, look instead at
[Building Android apps with native code using Meson](https://nibblestew.blogspot.com/2025/10/building-android-apps-with-native-code.html).

* `manifest`: The AndroidManifest.xml file describing your application
* `sources`: java source files are jars that compose your application
* `app_id`: the application package identifier (typically a domain you
            control in big endian format). This is optional if the
            manifest already contains a package id.
* `target_sdk`: The SDK version your application targets
* `min_sdk`: The lowest SDK version your application still supports
* `resources`: Files that will be added as resources to the APK (i.e.
               drawables, layouts, etc.). *Note:* the directory each
               file resides in has to match the resource group that
               it is a part of.
* `install`: if true, install the apk file
* `install_dir`: location to install the apk file to
* `install_tag`: A string used by the `meson install --tags` command
                 to install only a subset of the files.

Returns the target that produces the APK

*Added 1.11.0*
