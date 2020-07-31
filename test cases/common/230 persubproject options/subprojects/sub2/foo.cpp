#include <memory>

class Dummy {
  int x;
};

int foo() {
  auto obj = std::make_shared<Dummy>();
  return 0;
}
