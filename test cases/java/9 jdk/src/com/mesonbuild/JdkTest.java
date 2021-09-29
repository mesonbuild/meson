package com.mesonbuild;

public final class JdkTest {
    private static native int jdk_test();

    public static void main(String[] args) {
        if (jdk_test() != 0xdeadbeef) {
            throw new RuntimeException("jdk_test() did not return 0");
        }
    }

    static {
        System.loadLibrary("jdkjava");
    }
}
