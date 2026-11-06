# A custom target in another directory, used as an input by sub/dir.
gen_txt = custom_target(
  'gen_txt',
  command: [python, '-c', 'import sys; open(sys.argv[1], "w").write("gen")', '@OUTPUT@'],
  output: 'gen.txt',
)
