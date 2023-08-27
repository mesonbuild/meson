## Shader language support

Added support for shader program compilation. This includes
the GLSL language, glslc compiler, and the new shader() function.
Also adds the options `glsl_target_env`, `glsl_target_spv` and `glsl_std`
to default_options to control different aspects of the GLSL compiler.

```meson
project('shaders', 'glsl')

shader('example', 'example.vert')
```
