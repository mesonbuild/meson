#pragma once
#include <QObject>
#include <QQmlEngine>

class QmlCppExposed : public QObject
{
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(int foo READ getFoo WRITE setFoo NOTIFY fooChanged)

public:
    inline int getFoo() const { return m_foo; }
    inline void setFoo(int value) {
        if (value == m_foo)
            return;
        m_foo = value;
        emit fooChanged();
    }

signals:
    void fooChanged();

private:
    int m_foo = 42;
};
