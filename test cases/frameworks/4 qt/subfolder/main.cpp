#include <QImage>
#include <QFile>
#include <QString>

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
  QFile file(":/txt_resource.txt");
  if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
      return 1;
  QString line = file.readLine();
  if(line.compare("Hello World"))
      return 1;
  return 0;
}