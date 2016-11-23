project('llvm-ir', 'c', 'cpp')

foreach lang : ['c', 'cpp']
  cc_id = meson.get_compiler(lang).get_id()
  if cc_id == 'clang'
    e = executable('square_ir_' + lang, 'square.ll', 'main.' + lang)
    test('test IR square' + lang, e)
  endif
  # FIXME: msvc does not support passing assembly to cl.exe, but you can pass
  # it to ml.exe and get a compiled object. Meson should add support for
  # transparently building assembly with ml.exe with MSVC.
  if cc_id != 'msvc'
    cpu = host_machine.cpu_family()
    e = executable('square_asm_' + lang, 'square-' + cpu + '.S', 'main.' + lang)
    test('test ASM square' + lang, e, args : [e.full_path()])
  endif
endforeach
