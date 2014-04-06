#include<QObject>

class MocClass : public QObject {
    Q_OBJECT
};

int mocfunc() {
    MocClass m;
    return 0;
}

#include"mocmocinclude.moc"
