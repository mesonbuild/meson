zip_output = custom_target('genzip',
  input: xmlloc,
  output: 'registry.zip',
  command: [find_program('genzip.py'), '@OUTPUT@', '@INPUT@'])
