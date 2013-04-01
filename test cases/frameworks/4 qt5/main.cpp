#include <QApplication>
#include "mainWindow.h"

int main(int argc, char **argv) {
  QApplication app(argc, argv);
  MainWindow *win = new MainWindow();
  win->setWindowTitle("Button demo app");
  win->show();

  return app.exec();
}
