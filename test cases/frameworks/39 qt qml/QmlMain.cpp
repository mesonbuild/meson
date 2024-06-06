#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QDebug>

//extern type registration
extern void qml_register_types_My_Module6();

int main(int argCount, char* argVector[])
{
    //register resources from static libraries
    Q_INIT_RESOURCE(My_Module6);
    Q_INIT_RESOURCE(qmlcache_My_Module6);
    qml_register_types_My_Module6();

    //don't require a grapical environment to run the test
    qputenv("QT_QPA_PLATFORM", "offscreen");

    QGuiApplication app(argCount, argVector);
    QQmlApplicationEngine engine;

    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated, [](QObject *object, const QUrl &url){
        if (object == nullptr) {
            qFatal("unable to load scene");
        }
    });

    engine.addImportPath("qrc:///qt/qml");
    engine.addImportPath("qrc:///test");
    engine.load("qrc:///qt/qml/My/Module0/Main.qml");
    return app.exec();
}
