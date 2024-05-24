#include <napi.h>
#include <exception>

using namespace Napi;

Napi::String Method(const Napi::CallbackInfo &info) {
  Napi::Env env = info.Env();
  /* Test exception handling */
  try {
    throw std::logic_error{"test"};
  } catch(const std::exception &) {}
  return Napi::String::New(env, "world");
}

Napi::Object Init(Napi::Env env, Napi::Object exports) {
  exports.Set(Napi::String::New(env, "HelloWorld"),
              Napi::Function::New(env, Method));
  return exports;
}

NODE_API_MODULE(addon, Init)
