sc = run_command(grabber)
subsources = sc.stdout().strip().split(newline)

se = executable('subprog', subsources)
test('subgrabtest', se)
