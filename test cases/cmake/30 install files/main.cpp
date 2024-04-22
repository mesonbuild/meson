#include <fstream>
#include <iostream>
#include <string.h>
#include <vector>

using namespace std;

#ifdef TEST_READ
bool check(const char *file, const char *data) {
  ifstream ifs(file);
  auto size = ifs.tellg();
  ifs.seekg(0, ios::beg);
  if (size < 0) {
    cerr << "File " << file << " not found" << endl;
    return false;
  }
  vector<char> buffer(size);
  ifs.read(buffer.data(), size);
  if (memcmp(buffer.data(), data, size) != 0) {
    cerr << "Data " << data << " does not match " << buffer.data() << endl;
    return false;
  }
  return true;
}
#endif

int main(void) {
#ifdef TEST_READ
  if (!check(FILE_STATIC, DATA_STATIC)) return 1;
  if (!check(FILE_DYNAMIC, DATA_DYNAMIC)) return 1;
#endif
  return 0;
}
