#include <QImage>

int main(int argc, char **argv) {
  Q_INIT_RESOURCE(stuff3);
  QImage qi(":/thing.png");
  if(qi.width() != 640) {
      return 1;
  }
  return 0;
}