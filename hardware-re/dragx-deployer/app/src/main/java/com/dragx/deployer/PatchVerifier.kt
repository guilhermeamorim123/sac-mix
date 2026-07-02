package com.dragx.deployer

data class PatchCheck(
    val name: String,
    val offset: Long,
    val expectedBytes: ByteArray
)

data class PatchCheckResult(
    val name: String,
    val passed: Boolean,
    val expectedHex: String,
    val actualHex: String
)

object PatchVerifier {

    // File offsets and expected bytes are documented in hardware-re/dragx-app/NATIVE_PATCH.md
    // and encoded once already in hardware-re/dragx-app/tools/apply_native_patches.py.
    // Both refer to libnewcutjni.so from Upprinting_V7.0.3.005.apk specifically.

    val JNI_ONLOAD_CRASH_BYPASS = PatchCheck(
        name = "JNI_OnLoad crash bypass",
        offset = 0x160eeL,
        expectedBytes = byteArrayOf(0x00, 0xbf.toByte())
    )

    val CERTIFICATE_CHECK_BYPASS = PatchCheck(
        name = "getHandshake() certificate-check bypass",
        offset = 0x128d4L,
        expectedBytes = byteArrayOf(0x00, 0x20, 0x00, 0xbf.toByte())
    )

    val ALL_CHECKS = listOf(JNI_ONLOAD_CRASH_BYPASS, CERTIFICATE_CHECK_BYPASS)

    fun verify(check: PatchCheck, actualBytes: ByteArray): PatchCheckResult {
        val passed = actualBytes.contentEquals(check.expectedBytes)
        return PatchCheckResult(
            name = check.name,
            passed = passed,
            expectedHex = check.expectedBytes.toHex(),
            actualHex = actualBytes.toHex()
        )
    }

    private fun ByteArray.toHex(): String =
        joinToString(" ") { "%02x".format(it) }
}
