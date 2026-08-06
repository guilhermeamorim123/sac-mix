package com.cut.cutjni;

public class JniUtils {
    static {
        System.load("/data/local/tmp/libcrypto.so");
        System.load("/data/local/tmp/libssl.so");
        System.load("/data/local/tmp/libnewcutjni.so");
    }

    public static native char[] cmd_GetPassWordCutChar(String str);

    public static native String convertNumber(String str);

    public static native char[] convertNumber2(java.util.ArrayList<String> arrayList, String str);

    public static native String encryptSign();

    public static native byte[] getHandshake(long j2);
}
