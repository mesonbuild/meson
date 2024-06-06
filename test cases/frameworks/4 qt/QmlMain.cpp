#include <QGuiApplication>
#include <QQmlApplicationEngine>

int main(int argCount, char* argVector[])
{
    QGuiApplication app(argCount, argVector);
    QQmlApplicationEngine engine;
    engine.load("qrc:///qt/qml/Foo/Bar/QmlStuff.qml");
    app.exec();
}
