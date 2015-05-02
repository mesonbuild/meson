#include <QApplication>
#include "mainWindow.h"

int main(int argc, char **argv) {
  QApplication app(argc, argv);
  MainWindow *win = new MainWindow();
  QImage qi(":/thing.png");
  if(qi.width() != 640) {
      return 1;
  }
  QImage qi2(":/thing2.png");
  if(qi2.width() != 640) {
      return 1;
  }
  win->setWindowTitle("Meson Qt4 build test");

  win->show();
  return app.exec();
  return 0;
}
