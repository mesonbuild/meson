#pragma once
#include <QObject>
#include <QQmlEngine>

#include "QmlCppExposed.hpp"

class SubdirHeader : public QObject
{
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(int ok READ getOk WRITE setOk NOTIFY okChanged)

public:
    inline int getOk() const { return m_ok; }
    inline void setOk(int value) {
        if (value == m_ok)
            return;
        m_ok = value;
        emit okChanged();
    }

signals:
    void okChanged();

private:
    int m_ok = 6;
};
