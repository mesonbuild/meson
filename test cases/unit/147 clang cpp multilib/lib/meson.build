project('clang cpp multilib producer', 'cpp')

foreach variant : ['eh_rtti', 'noeh_rtti', 'eh_nortti', 'noeh_nortti']
  static_library(variant, '../marker.cpp', cpp_args: '-DMARKER=marker_' + variant, install: true)
endforeach
