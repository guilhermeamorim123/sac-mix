package com.dragx.deployer

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AdbOutputParserTest {

    @Test
    fun `connect success is detected`() {
        val result = AdbResult(0, "connected to 192.168.15.13:5555\n", "")
        assertTrue(AdbOutputParser.isConnectSuccess(result))
    }

    @Test
    fun `already connected is detected as success`() {
        val result = AdbResult(0, "already connected to 192.168.15.13:5555\n", "")
        assertTrue(AdbOutputParser.isConnectSuccess(result))
    }

    @Test
    fun `connect failure is detected`() {
        val result = AdbResult(1, "", "unable to connect to 192.168.15.13:5555: Connection refused\n")
        assertFalse(AdbOutputParser.isConnectSuccess(result))
    }

    @Test
    fun `install success is detected`() {
        val result = AdbResult(0, "Performing Streamed Install\nSuccess\n", "")
        assertTrue(AdbOutputParser.isInstallSuccess(result))
    }

    @Test
    fun `install failure is detected`() {
        val result = AdbResult(
            1,
            "Performing Streamed Install\n",
            "adb: failed to install DragX-signed.apk: INSTALL_FAILED_INSUFFICIENT_STORAGE\n"
        )
        assertFalse(AdbOutputParser.isInstallSuccess(result))
    }

    @Test
    fun `parses package dir from pm path output`() {
        val output = "package:/data/app/cn.upus.app.upprinting-2/base.apk\n"
        assertEquals("/data/app/cn.upus.app.upprinting-2", AdbOutputParser.parsePackageDir(output))
    }

    @Test
    fun `returns null when pm path output is empty`() {
        assertNull(AdbOutputParser.parsePackageDir(""))
    }
}
