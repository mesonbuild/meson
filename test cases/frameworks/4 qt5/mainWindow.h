#include <QObject>
#include <QMainWindow>
#include "ui_mainWindow.h"

class NotificationModel;

class MainWindow : public QMainWindow, private Ui_MainWindow {
    Q_OBJECT

public:
    MainWindow(QWidget *parent=0);
    ~MainWindow();

private:
};
