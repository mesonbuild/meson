#include <QImage>

int main(int argc, char **argv) {
  #ifndef UNITY_BUILD
  Q_INIT_RESOURCE(stuff3);
  Q_INIT_RESOURCE(stuff4);
  #endif

  QImage img1(":/thing.png");
  if(img1.width() != 640) {
      return 1;
  }
  QImage img2(":/thing4.png");
  if(img2.width() != 640) {
      return 1;
  }
  return 0;
}