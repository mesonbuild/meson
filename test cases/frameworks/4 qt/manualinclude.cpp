#include"manualinclude.h"
#include<QCoreApplication>

#include<QObject>

ManualInclude::ManualInclude() {
}

class MocClass : public QObject {
    Q_OBJECT
};

int main(int argc, char **argv) {
    ManualInclude mi;
    MocClass mc;
    return 0;
}

#include"manualinclude.moc"

