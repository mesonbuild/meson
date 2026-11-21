# A custom target in another directory, used by sub/dir both as an input
# and as a plain command argument.
gen_txt = custom_target(
  'gen_txt',
  command: [python, '-c', 'import sys; open(sys.argv[1], "w").write("gen")', '@OUTPUT@'],
  output: 'gen.txt',
)
