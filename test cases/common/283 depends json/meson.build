project('depjson')

dep = declare_dependency(include_directories: ['.'])

check_json = find_program('check_json.py')
custom_target('check',
    command: [check_json, dep.as_json(), '@OUTPUT@'],
    output: 'ok1',
    build_by_default: true,
)

# ensure that calling dep.as_json() twice doesn't fail
custom_target('check2',
    command: [check_json, dep.as_json(), '@OUTPUT@'],
    output: 'ok2',
    build_by_default: true,
)
