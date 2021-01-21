#include <jni.h>

#include "com_mesonbuild_JdkTest.h"

JNIEXPORT jint JNICALL Java_com_mesonbuild_JdkTest_jdk_1test
  (JNIEnv *env, jclass clazz)
{
    return (jint)0xdeadbeef;
}
