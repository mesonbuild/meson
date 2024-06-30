## Added support for passing generated lists as a dependency to gnome.compile_resources()

This allows to use output of preprocessors such as `blueprint-compiler` easily and reliably:

```meson
blueprint_generator = generator(
  find_program('blueprint-compiler'),
  output: '@BASENAME@.ui',
  arguments: ['compile', '--output', '@OUTPUT@', '@INPUT@']
)

blueprints = blueprint_generator.process(
  'Window.blp',
  'Widgets/FancyRow.plp',
  preserve_path_from: meson.current_source_dir()
)

gnome.compile_resources(
  'myapp',
  'myapp.gresource.xml',
  c_name: 'myapp',
  dependencies: blueprints
)
```
