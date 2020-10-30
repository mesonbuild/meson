project('cargo target cfg dependencies', 'rust')

rust = import('unstable-rust')

main1 = configure_file(
  input : 'exe.rs.in',
  output : 'exe1.rs',
  configuration : {'crate': 'sub1'},
)
sub1 = rust.subproject('sub1')
exe = executable('exe', main1, dependencies : sub1.get_variable('dep'))

main2 = configure_file(
  input : 'exe.rs.in',
  output : 'exe2.rs',
  configuration : {'crate': 'sub3'},
)
sub3 = rust.subproject('sub3')
exe2 = executable('exe2', main2, dependencies : sub3.get_variable('dep'))

main3 = configure_file(
  input : 'exe.rs.in',
  output : 'exe3.rs',
  configuration : {'crate': 'sub4'},
)
sub4 = rust.subproject('sub4')
exe2 = executable('exe3', main3, dependencies : sub4.get_variable('dep'))

if host_machine.system() == 'linux' and host_machine.cpu_family() == 'x86_64'
  main5 = configure_file(
    input : 'exe.rs.in',
    output : 'exe5.rs',
    configuration : {'crate': 'sub5'},
  )
  sub5 = rust.subproject('sub5')
  exe2 = executable('exe5', main5, dependencies : sub5.get_variable('dep'))
endif