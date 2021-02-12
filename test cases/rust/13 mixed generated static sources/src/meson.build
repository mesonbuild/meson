gen1_rs = custom_target(
  'gen1_rs',
  output : 'gen1.rs',
  command : [prog_gen, '@OUTPUT@'],
)

exe1 = executable(
  'exe1',
  ['main1.rs', gen1_rs],
)

test('custom_target', prog_test, args : [exe1, 'I prefer tarnish, actually.'])

gen2_rs = configure_file(
  input : 'gen2.rs.in',
  output : 'gen2.rs',
  copy : true,
)

exe2 = executable(
  'exe2',
  ['main2.rs', gen2_rs],
)

test('configure_file', prog_test, args : [exe2, 'Not me, Rust is best!'])

exe3 = executable(
  'exe3',
  ['main3.rs', gen1_rs, gen2_rs],
)

test('custom_target and configure_file mixed', prog_test, args : [exe3, 'I prefer tarnish, actually.\nNot me, Rust is best!'])
