project('depjson')

dep = declare_dependency(include_directories: ['.'])

check_json = find_program('check_json.py')
custom_target('check',
    command: [check_json, dep.as_json(), '@OUTPUT@'],
    output: 'ok',
    build_by_default: true,
)
