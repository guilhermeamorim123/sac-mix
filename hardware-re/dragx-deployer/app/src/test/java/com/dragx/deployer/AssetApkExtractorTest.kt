package com.dragx.deployer

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.File

class AssetApkExtractorTest {

    @Test
    fun `copies asset bytes exactly to destination file`() {
        val fakeApkBytes = byteArrayOf(0x50, 0x4b, 0x03, 0x04, 0x00, 0x01, 0x02)
        val destination = File.createTempFile("dragx-test", ".apk")
        destination.deleteOnExit()

        val result = AssetApkExtractor.extract(ByteArrayInputStream(fakeApkBytes), destination)

        assertTrue(result.exists())
        assertArrayEquals(fakeApkBytes, result.readBytes())
    }
}
