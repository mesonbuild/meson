project('clang cpp multilib', 'cpp')

foreach variant : [
  ['eh_rtti', 'default', 'true'],
  ['noeh_rtti', 'none', 'true'],
  ['eh_nortti', 'default', 'false'],
  ['noeh_nortti', 'none', 'false'],
]
  executable(variant[0], 'main.cpp',
    override_options: ['cpp_eh=' + variant[1], 'cpp_rtti=' + variant[2]],
    cpp_args: '-DREQUIRED=marker_' + variant[0],
    link_args: ['-lprobe', '-Wl,-e,main'])
endforeach

executable('override', 'main.cpp',
  override_options: ['cpp_eh=none', 'cpp_rtti=false',
                    'cpp_link_args=-nostdlib -fexceptions -frtti'],
  cpp_args: '-DREQUIRED=marker_eh_rtti',
  link_args: ['-lprobe', '-Wl,-e,main'])
