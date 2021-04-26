project('find program override', 'c')

gencodegen = find_program('gencodegen', required : false)

assert(not gencodegen.found(), 'gencodegen is an internal program, should not be found')

# Test the check-if-found-else-override workflow
if not gencodegen.found()
  subdir('subdir')
endif

subdir('otherdir')

tool = find_program('sometool')
assert(tool.found())
