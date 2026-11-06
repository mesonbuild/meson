export module lib;

export import :detail;

export int lib_value() {
  return detail_value() + 41;
}
