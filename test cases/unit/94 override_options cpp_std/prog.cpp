#include <cstdio>
#include <string>
#include <variant>

struct Error {
    std::string name;
};

using Result = std::variant<bool, const Error>;

int main (int ac, char **av)
{
  return 0;
}
