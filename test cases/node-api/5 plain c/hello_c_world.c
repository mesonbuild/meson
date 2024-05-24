#include <node_api.h>

#define NODE_API_CALL(env, call)                                               \
  do {                                                                         \
    napi_status status = (call);                                               \
    if (status != napi_ok) {                                                   \
      const napi_extended_error_info *error_info = NULL;                       \
      napi_get_last_error_info((env), &error_info);                            \
      const char *err_message = error_info->error_message;                     \
      bool is_pending;                                                         \
      napi_is_exception_pending((env), &is_pending);                           \
      /* If an exception is already pending, don't rethrow it */               \
      if (!is_pending) {                                                       \
        const char *message =                                                  \
            (err_message == NULL) ? "empty error message" : err_message;       \
        napi_throw_error((env), NULL, message);                                \
      }                                                                        \
      return NULL;                                                             \
    }                                                                          \
  } while (0)

static napi_value DoSomethingUseful(napi_env env, napi_callback_info info) {
  static const char *text = "Hello C World";
  napi_value result;
  NODE_API_CALL(env,
                napi_create_string_utf8(env, text, NAPI_AUTO_LENGTH, &result));
  return result;
}

napi_value create_addon(napi_env env) {
  napi_value result;
  NODE_API_CALL(env, napi_create_object(env, &result));

  napi_value exported_function;
  NODE_API_CALL(env, napi_create_function(env, "HelloWorld",
                                          NAPI_AUTO_LENGTH, DoSomethingUseful,
                                          NULL, &exported_function));

  NODE_API_CALL(env, napi_set_named_property(env, result, "HelloWorld",
                                             exported_function));

  return result;
}

NAPI_MODULE_INIT() { return create_addon(env); }
