package com.mesonbuild;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.IOException;

public final class JniTest {
    private static String libname = "jnijava";
    static {
        String fullname = System.mapLibraryName(libname);
        // this is somewhat hacky, but attempt to split off the extension
        int ext = fullname.indexOf(".");
        if (ext < 0)
            ext = fullname.length();
        try {
            File fslib = File.createTempFile(fullname.substring(0, ext), fullname.substring(ext));
            fslib.setReadable(true);
            fslib.setWritable(true, true);
            fslib.setExecutable(true);

            InputStream istream = JniTest.class.getResourceAsStream("/" + fullname);
            FileOutputStream ostream = new FileOutputStream(fslib);
            istream.transferTo(ostream);
            istream.close();
            ostream.close();

            System.load(fslib.getAbsolutePath());

            fslib.deleteOnExit();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    private static native int jni_test();

    public static void main(String[] args) {
        if (jni_test() != Configured.FINGERPRINT) {
            throw new RuntimeException("jdk_test() did not return 0");
        }
    }
}
