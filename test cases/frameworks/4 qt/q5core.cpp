#include <QCoreApplication>

int main(int argc, char **argv) {
  QCoreApplication app(argc, argv);

  // Don't actually start the main loop so this
  // can be run as a unit test.
  //return app.exec();
  return 0;
}
