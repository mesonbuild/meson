#include <windows.h>
#include <shellapi.h>

int main() {
  char path[MAX_PATH];
  FindExecutableA("cmd.exe", 0, path);
  return 0;
}
