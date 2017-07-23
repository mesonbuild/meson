# GNOME module

This module provides helper tools for build operations needed when building Gnome/GLib programs.

**Note**: the compilation commands here might not work properly when you change the source files. This is a bug in the respective compilers which do not expose the required dependency information. This has been reported upstream in [this bug]. Until this is fixed you need to be careful when changing your source files.

  [this bug]: https://bugzilla.gnome.org/show_bug.cgi?id=745754

## Usage

To use this module, just do: **`gnome = import('gnome')`**. The following functions will then be available as methods on the object with the name `gnome`. You can, of course, replace the name `gnome` with anything else.

### gnome.compile_resources()

This function compiles resources specified in an XML file into code that can be embedded inside the main binary. Similar a build target it takes two positional arguments. The first one is the name of the resource and the second is the XML file containing the resource definitions. If the name is `foobar`, Meson will generate a header file called `foobar.h`, which you can then include in your sources.

* `source_dir`: a list of subdirectories where the resource compiler should look up the files, relative to the location of the XML file
* `c_name`: passed to the resource compiler as an argument after `--c-name`
* `dependencies`: extra targets to depend upon for building
* `export`: (*Added 0.37.0*) if true, export the symbols of the generated sources
* `gresource_bundle`: (*Added 0.37.0*) if true, output a `.gresource` file instead of source
* `install_header`: (*Added 0.37.0*) if true, install the header file
* `install`: (*Added 0.37.0*) if true, install the gresource file
* `install_dir`: (*Added 0.37.0*) location to install the header or bundle depending on previous options
* `extra_args`: extra command line arguments to pass to the resource compiler

Returns an array containing: `[c_source, header_file]` or `[gresource_bundle]`

### gnome.generate_gir()

Generates GObject introspection data. Takes one positional argument, the build target you want to build gir data for. There are several keyword arguments. Many of these map directly to the `g-ir-scanner` tool so see its documentation for more information.

* `sources`: the list of sources to be scanned for gir data
* `nsversion`: namespace version
* `namespace`: the namespace for this gir object which determines output files
* `symbol_prefix`: the symbol prefix for the gir object, e.g. `gtk`
* `identifier_prefix`: the identifier prefix for the gir object, e.g. `Gtk`
* `export_packages`: extra packages the gir file exports
* `includes`: list of gir names to be included, can also be a GirTarget
* `dependencies`: deps to use during introspection scanning
* `link_with`: list of libraries to link with
* `include_directories`: extra include paths to look for gir files
* `install`: if true, install the generated files
* `install_dir_gir`: (*Added 0.35.0*) which directory to install the gir file into
* `install_dir_typelib`: (*Added 0.35.0*) which directory to install the typelib file into
* `extra_args`: command line arguments to pass to gir compiler

Returns an array of two elements which are: `[gir_target, typelib_target]`

### gnome.genmarshal()

Generates a marshal file using the `glib-genmarshal` tool. The first argument is the basename of
the output files.

* `sources`: the list of sources to use as inputs
* `prefix`: the prefix to use for symbols
* `install_header`: if true, install the generated header
* `install_dir`: directory to install header to
* `stdinc`: if true, include the standard marshallers from glib
* `nostdinc`: if true, don't include the standard marshallers from glib
* `internal`: if true, mark generated sources as internal
* `skip_source`: if true, skip source location comments
* `valist_marshallers`: if true, generate va_list marshallers
* `extra_args`: (*Added 0.42.0*) additional command line arguments to pass
  to `glib-genmarshal` (*Requires GLib 2.54*)

*Added 0.35.0*

Returns an array of two elements which are: `[c_source, header_file]`

### gnome.mkenums()

Generates enum files for GObject using the `glib-mkenums` tool. The first argument is the base name of the output files.

Note that if you `#include` the generated header in any of the sources for a build target, you must add the generated header to the build target's list of sources to codify the dependency. This is true for all generated sources, not just `mkenums`.

* `sources`: the list of sources to make enums with
* `c_template`: template to use for generating the source
* `h_template`: template to use for generating the header
* `install_header`: if true, install the generated header
* `install_dir`: directory to install the header
* `comments`: comment passed to the command
* `identifier_prefix`: prefix to use for the identifiers
* `symbol_prefix`: prefix to use for the symbols
* `eprod`: enum text
* `fhead`: file header
* `fprod`: file text
* `ftail`: file tail
* `vhead`: value text
* `vtail`: value tail

*Added 0.35.0*

Returns an array of two elements which are: `[c_source, header_file]`

### gnome.compile_schemas()

When called, this method will compile the gschemas in the current directory. Note that this is not
for installing schemas and is only useful when running the application locally for example during tests.

### gnome.gdbus_codegen()

Compiles the given XML schema into gdbus source code. Takes two positional arguments, the first one specifies the name of the source files and the second specifies the XML file name. There are three keyword arguments. `interface_prefix` and `namespace` map to corresponding features of the compiler while `object_manager` (since 0.40.0), when set to true, generates object manager code.

Returns an opaque object containing the source files. Add it to a top level target's source list.

### gnome.generate_vapi()

Creates a VAPI file from gir. The first argument is the name of the library.

* `sources`: the gir source to generate the VAPI from
* `packages`: VAPI packages that are depended upon
* `metadata_dirs`: extra directories to include for metadata files
* `gir_dirs`: extra directories to include for gir files
* `vapi_dirs`: extra directories to include for VAPI files
* `install`: if true, install the VAPI file
* `install_dir`: location to install the VAPI file (defaults to datadir/vala/vapi)

Returns a custom dependency that can be included when building other VAPI or Vala binaries.

*Added 0.36.0*

### gnome.yelp()

Installs help documentation using Yelp. The first argument is the project id.

This also creates two targets for translations `help-$project-update-po` and `help-$project-pot`.

* `sources`: list of pages
* `media`: list of media such as images
* `symlink_media`: if media should be symlinked not copied (defaults to `true` since 0.42.0)
* `languages`: list of languages for translations

Note that very old versions of yelp may not support symlinked media; At least 3.10 should work.

*Added 0.36.0*

### gnome.gtkdoc()

Compiles and installs gtkdoc documentation into `prefix/share/gtk-doc/html`. Takes one positional argument: The name of the module.

* `main_xml`: specifies the main XML file
* `main_sgml`: equal to `main_xml`
* `src_dir`: include_directories to include
* `dependencies`: a list of dependencies
* `install`: if true, installs the generated docs
* `install_dir`: the directory to install the generated docs relative to the gtk-doc html dir or an absolute path (default: module name)
* `scan_args`: a list of arguments to pass to `gtkdoc-scan`
* `scanobjs_args`: a list of arguments to pass to `gtkdoc-scangobj`
* `gobject_typesfile`: a list of type files
* `fixxref_args`: a list of arguments to pass to `gtkdoc-fixxref`
* `html_args` a list of arguments to pass to `gtkdoc-mkhtml`
* `html_assets`: a list of assets for the HTML pages
* `content_files`: a list of content files
* `mkdb_args`: a list of arguments to pass to `gtkdoc-mkdb`

This creates a `$module-doc` target that can be ran to build docs and normally these are only built on install.

### gnome.gtkdoc_html_dir()

Takes as argument a module name and returns the path where that module's HTML files will be installed. Usually used with `install_data` to install extra files, such as images, to the output directory.
