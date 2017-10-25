#include"manualinclude.h"
#include<QCoreApplication>

#include<QObject>

ManualInclude::ManualInclude() {
}

class MocClass : public QObject {
    Q_OBJECT
};

void testSlot() {
	;
}

int main(int argc, char **argv) {
    ManualInclude mi;
    MocClass mc;
    QObject::connect(&mi, &ManualInclude::mysignal, &testSlot);
    return 0;
}

#include"manualinclude.moc"

