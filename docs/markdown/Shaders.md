---
title: Shaders
short-description: Compiling shader programs
...

# Compiling shader programs

Meson has support for compiling shaders written in GLSL. This is done through the shader() function:

```meson
project('shader_example', 'glsl')

shader('example_shader_program', 'example.vert')
```
