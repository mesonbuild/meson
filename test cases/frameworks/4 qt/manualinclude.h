#ifndef MANUALINCLUDE_H_
#define MANUALINCLUDE_H_

#include<QObject>

class ManualInclude : public QObject {
    Q_OBJECT

public:
    ManualInclude();

signals:
    int mysignal();
};

#endif
