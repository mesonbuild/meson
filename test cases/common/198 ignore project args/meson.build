project('ignore project args', 'c')

add_project_arguments('-broken', language : 'c')
add_project_link_arguments('-Wl,-broken-link', language : 'c')

app = executable('testapp', 'main.c',
  ignore_project_args : true,
  ignore_project_link_args : true,
)

test('test-ignore-project-args', app)
