#pragma once

class CmMod {
private:
  int num = 0;

public:
  inline int getNum() const { return num; }
  void asyncIncrement();
};
