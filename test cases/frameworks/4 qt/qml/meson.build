qmlmodule1 = qtmodule.qml_module(
    qt + 'qmlmodule1',
    'My.Module1',
    '1.0',
    qml_sources: files('Basic.qml', 'subdir/Thing.qml'),
    qml_singletons: files('QmlSingleton.qml'),
    qml_internals: files('Internal.qml'),
    moc_headers: files('QmlCppExposed.hpp', 'QmlCppOtherExposed.hpp'),
    designer_supported: true,
    dependencies: [qtdep],
    install: true
)

#with a different resource prefix
qmlmodule2 = qtmodule.qml_module(
    qt + 'qmlmodule2',
    'My.Module2',
    '1.0',
    qml_sources: files('Basic.qml', 'subdir/Thing.qml'),
    resources_prefix: '/test',
    dependencies: [qtdep],
)

#build without cachegen
qmlmodule3 = qtmodule.qml_module(
    qt + 'qmlmodule3',
    'My.Module3',
    '1.10',
    qml_sources: files('Basic.qml', 'subdir/Thing.qml'),
    cachegen: false,
    dependencies: [qtdep],
)

#build without cachegen
qmlmodule4 = qtmodule.qml_module(
    qt + 'qmlmodule4',
    'My.Module4',
    '1.10',
    qml_sources: files('Basic.qml', 'subdir/Thing.qml'),
    generate_qmldir: false,
    dependencies: [qtdep],
)
qmlmodule4_res = qtmodule.compile_resources(
    name : qt + 'qmlmodule4_resource',
    sources : files(['custom_qmldir.qrc']),
    method : get_option('method')
)

#qml entry point and qmldir dependecies
qmlmodule0 = qtmodule.qml_module(
    'qmlmodule0',
    'My.Module0',
    '1.0',
    qml_sources: files('Main.qml'),
    imports: ['QtQuick/2.0', 'My.Module1'],
    optional_imports: ['My.Module2/auto'],
    dependencies: [qtdep],
)


qmltest = executable(qt + '_qmlmodule',
                     sources : ['QmlMain.cpp', qmlmodule0, qmlmodule1, qmlmodule2, qmlmodule3, qmlmodule4, qmlmodule4_res],
                     dependencies : qtdep)
