#include <string>

class cmModClass {
private:
  std::string str;

public:
  cmModClass(const std::string &foo);
  std::string getStr() const;
};
