project('package test', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')
cargo_ws = rust.workspace()

hello_rs = cargo_ws.subproject('hello')
assert(hello_rs.name() == 'hello')
assert(hello_rs.version() == '3.0.0')
assert(hello_rs.api() == '3')

answer_rs = cargo_ws.subproject('answer', '2')
assert(answer_rs.name() == 'answer')
assert(answer_rs.version() == '2.1.0')
assert(answer_rs.api() == '2')

e = executable('package-test', 'src/main.rs',
  dependencies: [hello_rs.dependency(), answer_rs.dependency()],
)
