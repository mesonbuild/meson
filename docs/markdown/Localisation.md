---
short-description: Localization with GNU Gettext
...

# Localisation

Localising your application with GNU gettext takes a little effort but is quite straightforward. This documentation assumes that you have a `po` subdirectory at your project root directory that contains all the localisation info.

The first thing you need is a file called `POTFILES`. It lists all the source files that gettext should scan in order to find strings to translate. The syntax of the file is one line per source file and the line must contain the relative path from source root. A sample POTFILES might look like this.

    src/file1.c
    src/file2.c
    src/subdir/file3.c
    include/mything/somefile.h

We also need to define an array of strings containing all the locales we want to generate. This is done in the Meson file in the `po` subdirectory. Assuming we want to generate Finnish and German localisations, the definition would look like this.

```meson
langs = ['fi', 'de']
```

Then we need to generate the main pot file. Usually this is generated manually or exists already. If not, see later on how to generate it using Meson. The potfile can have any name but is usually the name of the gettext package. Let's say the project is called *intltest*. In this case the corresponding pot file would be called `intltest.pot`.

For each language listed in the array above we need a corresponding `.po` file. This has to be generated manually, see the gettext manual for details. Once we have all this, we can define the localisation to Meson with these lines.

```meson
i18n = import('i18n')
langs = ['fi', 'de']
i18n.gettext('intltest', languages : langs)
```

The first command imports the `i18n` module that provides gettext features. The third line does the actual invocation. The first argument is the gettext package name. This causes two things to happen. The first is that Meson will generate binary mo files and put them to their proper locations when doing an install. The second is that it creates a build rule to regenerate the main pot file. If you are using the Ninja backend, this is how you would invoke the rebuild.

```console
$ ninja intltest-pot
```

If the pot file does not yet exist, it will be created. It is recommended to inspect it manually afterwards and fill in e.g. proper copyright and contact information.

Meson does not currently have built in commands for generating po files from the pot file. This is because translations are usually done by people who are not developers and thus have their own workflows.
