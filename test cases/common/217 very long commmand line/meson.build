project('very long command lines', 'c')

seq = run_command('seq.py', '1', '256').stdout().strip().split('\n')

sources = []
codegen = find_program('codegen.py')

foreach i : seq
  sources += custom_target('codegen' + i,
                           command: [codegen, i, '@OUTPUT@'],
                           output: 'test' + i + '.c')
endforeach

shared_library('sharedlib', sources)
static_library('staticlib', sources)
executable('app', 'main.c', sources)
