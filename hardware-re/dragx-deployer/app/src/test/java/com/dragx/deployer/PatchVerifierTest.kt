package com.dragx.deployer

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PatchVerifierTest {

    @Test
    fun `jni onload check passes with patched bytes`() {
        val patchedBytes = byteArrayOf(0x00, 0xbf.toByte())
        val result = PatchVerifier.verify(PatchVerifier.JNI_ONLOAD_CRASH_BYPASS, patchedBytes)
        assertTrue(result.passed)
    }

    @Test
    fun `jni onload check fails with original unpatched bytes`() {
        val originalBytes = byteArrayOf(0x04, 0xbf.toByte())
        val result = PatchVerifier.verify(PatchVerifier.JNI_ONLOAD_CRASH_BYPASS, originalBytes)
        assertFalse(result.passed)
    }

    @Test
    fun `certificate check passes with patched bytes`() {
        val patchedBytes = byteArrayOf(0x00, 0x20, 0x00, 0xbf.toByte())
        val result = PatchVerifier.verify(PatchVerifier.CERTIFICATE_CHECK_BYPASS, patchedBytes)
        assertTrue(result.passed)
    }

    @Test
    fun `certificate check fails with original unpatched bytes`() {
        val originalBytes = byteArrayOf(0xf9.toByte(), 0xf7.toByte(), 0x10, 0xea.toByte())
        val result = PatchVerifier.verify(PatchVerifier.CERTIFICATE_CHECK_BYPASS, originalBytes)
        assertFalse(result.passed)
    }

    @Test
    fun `failure result reports both expected and actual hex`() {
        val wrongBytes = byteArrayOf(0x11, 0x22)
        val result = PatchVerifier.verify(PatchVerifier.JNI_ONLOAD_CRASH_BYPASS, wrongBytes)
        assertEquals("00 bf", result.expectedHex)
        assertEquals("11 22", result.actualHex)
    }

    @Test
    fun `ALL_CHECKS contains exactly the two known patches in order`() {
        assertEquals(2, PatchVerifier.ALL_CHECKS.size)
        assertEquals("JNI_OnLoad crash bypass", PatchVerifier.ALL_CHECKS[0].name)
        assertEquals(0x160eeL, PatchVerifier.ALL_CHECKS[0].offset)
        assertEquals("getHandshake() certificate-check bypass", PatchVerifier.ALL_CHECKS[1].name)
        assertEquals(0x128d4L, PatchVerifier.ALL_CHECKS[1].offset)
    }
}
