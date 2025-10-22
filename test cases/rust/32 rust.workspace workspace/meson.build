project('workspace test', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')
cargo_ws = rust.workspace()

# Test workspace.packages() method
assert(cargo_ws.packages() == ['answer', 'hello', 'workspace_test'])

hello_rs = cargo_ws.subproject('hello')
assert(hello_rs.name() == 'hello')
assert(hello_rs.version() == '1.0.0')
assert(hello_rs.api() == '1')
assert(hello_rs.all_features() == ['default', 'goodbye'])
assert(hello_rs.features() == ['default', 'goodbye'])

answer_rs = cargo_ws.subproject('answer', '2')
assert(answer_rs.name() == 'answer')
assert(answer_rs.version() == '2.1.0')
assert(answer_rs.api() == '2')
assert(answer_rs.all_features() == ['default', 'large'])
assert(answer_rs.features() == ['default', 'large'])

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
