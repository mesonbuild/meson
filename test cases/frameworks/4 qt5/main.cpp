#include <QApplication>
#include "mainWindow.h"

int main(int argc, char **argv) {
  QApplication app(argc, argv);
  MainWindow *win = new MainWindow();
  QImage qi(":/thing.png");
  if(qi.width() != 640) {
      return 1;
  }
  win->setWindowTitle("Meson Qt5 build test");

  // Don't actually start the GUI so this
  // can be run as a unit test.
  //win->show();
  //return app.exec();
  return 0;
}
