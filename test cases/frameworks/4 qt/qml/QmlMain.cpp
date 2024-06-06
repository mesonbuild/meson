#include <QGuiApplication>
#include <QQmlApplicationEngine>

int main(int argCount, char* argVector[])
{
    QGuiApplication app(argCount, argVector);
    QQmlApplicationEngine engine;
    engine.addImportPath("qrc:///qt/qml");
    engine.addImportPath("qrc:///test");
    engine.load("qrc:///qt/qml/My/Module0/Main.qml");
    return app.exec();
}
