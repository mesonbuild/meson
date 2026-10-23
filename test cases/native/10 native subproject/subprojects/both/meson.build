project('both', 'c')

e = executable('main', 'main.c')
test('main', e)

# Run and alias targets have the same name for both machines.
alias_target('main-alias', e)

# Check that the same summary entry is accepted for both machines
summary('both', true)
