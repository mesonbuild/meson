#include <string>

class cmModInternalClass {
private:
  std::string str;

public:
  cmModInternalClass(const std::string &foo);
  std::string getStr() const;
};
