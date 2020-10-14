project('proj1', ['c'], version : '1.0.0')

cmake = import('cmake')

cmake.configure_package_config_file(
    name: meson.project_name(),
    input: 'proj1.cmake.in',
    configuration: configuration_data()
)


