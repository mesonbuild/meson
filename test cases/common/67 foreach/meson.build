project('foreach', 'c')

tests = [['test1', 'prog1', 'prog1.c'],
  ['test2', 'prog2', 'prog2.c'],
  ['test3', 'prog3', 'prog3.c']]

foreach i : tests
  test(i.get(0), executable(i.get(1), i.get(2), install : true))

  # Ensure that changing the tests variable does not
  # affect ongoing iteration in the foreach loop.
  #
  # Being able to do that would make Meson Turing complete and
  # we definitely don't want that.
  tests = ['test4', 'prog4', 'prog4.c']
endforeach
