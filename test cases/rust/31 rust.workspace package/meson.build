project('package test', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')
cargo = rust.workspace()

hello_rs = cargo.subproject('hello')
answer_rs = cargo.subproject('answer')

e = executable('package-test', 'src/main.rs',
  dependencies: [hello_rs.dependency(), answer_rs.dependency()],
)
test('package-test', e)

# failure test cases for dependency()
testcase expect_error('package.dependency.*must be one of c, proc-macro, rust.*', how: 're')
  hello_rs.dependency(rust_abi: 'something else')
endtestcase
testcase expect_error('Package hello does not support ABI c')
  hello_rs.dependency(rust_abi: 'c')
endtestcase
