project('workspace test', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')
cargo_ws = rust.workspace()

hello_dep = dependency('hello-1-rs')
answer_dep = dependency('answer-2-rs')

e = executable('workspace-test', 'src/main.rs',
  dependencies: [hello_dep, answer_dep],
)
test('workspace-test', e)
