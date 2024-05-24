#include <napi.h>

using namespace Napi;

class Worker : public Napi::AsyncWorker {
  Napi::Promise::Deferred deferred;
  bool reject;
  std::string value;

public:
  Worker(Napi::Env env, bool fail = false)
      : Napi::AsyncWorker{env, "worker"}, deferred{env}, reject(fail), value{} {
  }

  virtual void Execute() override {
    if (!reject)
      value = "world";
    else
      value = "not world";
  }

  virtual void OnOK() override {
    Napi::Env env{Env()};
    if (!reject)
      deferred.Resolve(Napi::String::New(env, value));
    else
      deferred.Reject(Napi::String::New(env, value));
  }

  Napi::Promise Promise() {
    return deferred.Promise();
  }
};

Napi::Promise Method(const Napi::CallbackInfo &info) {
  Napi::Env env{info.Env()};
  auto worker = new Worker(env);
  worker->Queue();
  return worker->Promise();
}

Napi::Object Init(Napi::Env env, Napi::Object exports) {
  exports.Set(Napi::String::New(env, "HelloWorld"),
              Napi::Function::New(env, Method));
  return exports;
}

NODE_API_MODULE(addon, Init)
