project('workspace test', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')
cargo_ws = rust.workspace()

hello_rs = cargo_ws.subproject('hello')
answer_rs = cargo_ws.subproject('answer', '2')

e = executable('workspace-test', 'src/main.rs',
  dependencies: [hello_rs.dependency(), answer_rs.dependency()],
)
test('workspace-test', e)

# failure test cases for dependency()
testcase expect_error('package.dependency.*must be one of c, proc-macro, rust.*', how: 're')
  hello_rs.dependency(rust_abi: 'something else')
endtestcase
testcase expect_error('Package hello does not support ABI c')
  hello_rs.dependency(rust_abi: 'c')
endtestcase
