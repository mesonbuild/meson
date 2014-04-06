#include<QCoreApplication>

int mocfunc();

int main(int argc, char **argv) {
  QCoreApplication app(argc, argv);

  return mocfunc();
}
