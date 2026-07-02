package com.dragx.deployer

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DeployControllerTest {

    private val fakeApkPath = "/tmp/DragX-signed.apk"
    private val fakePackageDir = "/data/app/cn.upus.app.upprinting-2"

    @Test
    fun `happy path reports overall success with both patches verified`() {
        val fake = FakeAdbRunner { args ->
            when {
                args == listOf("connect", "192.168.15.13:5555") ->
                    AdbResult(0, "connected to 192.168.15.13:5555\n", "")
                args == listOf("install", "-r", fakeApkPath) ->
                    AdbResult(0, "Performing Streamed Install\nSuccess\n", "")
                args == listOf("shell", "am", "force-stop", "cn.upus.app.upprinting") ->
                    AdbResult(0, "", "")
                args == listOf("shell", "pm", "path", "cn.upus.app.upprinting") ->
                    AdbResult(0, "package:$fakePackageDir/base.apk\n", "")
                args.size == 2 && args[0] == "shell" && args[1].contains("skip=90350") ->
                    AdbResult(0, "00 bf\n", "")
                args.size == 2 && args[0] == "shell" && args[1].contains("skip=75988") ->
                    AdbResult(0, "00 20 00 bf\n", "")
                else -> AdbResult(1, "", "unexpected call: $args")
            }
        }
        val controller = DeployController(fake, fakeApkPath)

        val report = controller.deploy("192.168.15.13:5555")

        assertTrue(report.overallSuccess)
        assertEquals(5, report.steps.size)
        assertTrue(report.steps.all { it is DeployStepResult.Success })
    }

    @Test
    fun `connect failure stops early and reports failure`() {
        val fake = FakeAdbRunner { args ->
            if (args == listOf("connect", "192.168.15.13:5555")) {
                AdbResult(1, "", "unable to connect to 192.168.15.13:5555: Connection refused\n")
            } else {
                AdbResult(1, "", "should not be called: $args")
            }
        }
        val controller = DeployController(fake, fakeApkPath)

        val report = controller.deploy("192.168.15.13:5555")

        assertFalse(report.overallSuccess)
        assertEquals(1, report.steps.size)
        assertTrue(report.steps.first() is DeployStepResult.Failure)
        assertEquals(1, fake.callLog.size)
    }

    @Test
    fun `install failure stops early without attempting verification`() {
        val fake = FakeAdbRunner { args ->
            when {
                args == listOf("connect", "192.168.15.13:5555") ->
                    AdbResult(0, "connected to 192.168.15.13:5555\n", "")
                args == listOf("install", "-r", fakeApkPath) ->
                    AdbResult(1, "", "adb: failed to install: INSTALL_FAILED_INSUFFICIENT_STORAGE\n")
                else -> AdbResult(1, "", "should not be called: $args")
            }
        }
        val controller = DeployController(fake, fakeApkPath)

        val report = controller.deploy("192.168.15.13:5555")

        assertFalse(report.overallSuccess)
        assertEquals(2, report.steps.size)
        assertTrue(report.steps.last() is DeployStepResult.Failure)
    }

    @Test
    fun `certificate patch mismatch reports overall failure naming the check`() {
        // Regression test for the exact historical bug this project hit:
        // app installs fine, but getHandshake() silently returns garbage
        // because the certificate-check patch didn't take. This must never
        // be reported as overall success.
        val fake = FakeAdbRunner { args ->
            when {
                args == listOf("connect", "192.168.15.13:5555") ->
                    AdbResult(0, "connected to 192.168.15.13:5555\n", "")
                args == listOf("install", "-r", fakeApkPath) ->
                    AdbResult(0, "Performing Streamed Install\nSuccess\n", "")
                args == listOf("shell", "am", "force-stop", "cn.upus.app.upprinting") ->
                    AdbResult(0, "", "")
                args == listOf("shell", "pm", "path", "cn.upus.app.upprinting") ->
                    AdbResult(0, "package:$fakePackageDir/base.apk\n", "")
                args.size == 2 && args[0] == "shell" && args[1].contains("skip=90350") ->
                    AdbResult(0, "00 bf\n", "")
                args.size == 2 && args[0] == "shell" && args[1].contains("skip=75988") ->
                    AdbResult(0, "f9 f7 10 ea\n", "") // original, unpatched bytes
                else -> AdbResult(1, "", "unexpected call: $args")
            }
        }
        val controller = DeployController(fake, fakeApkPath)

        val report = controller.deploy("192.168.15.13:5555")

        assertFalse(report.overallSuccess)
        val failure = report.steps.last() as DeployStepResult.Failure
        assertTrue(failure.message.contains("getHandshake"))
    }

    @Test
    fun `unparseable pm path output stops before verification`() {
        val fake = FakeAdbRunner { args ->
            when {
                args == listOf("connect", "192.168.15.13:5555") ->
                    AdbResult(0, "connected to 192.168.15.13:5555\n", "")
                args == listOf("install", "-r", fakeApkPath) ->
                    AdbResult(0, "Performing Streamed Install\nSuccess\n", "")
                args == listOf("shell", "am", "force-stop", "cn.upus.app.upprinting") ->
                    AdbResult(0, "", "")
                args == listOf("shell", "pm", "path", "cn.upus.app.upprinting") ->
                    AdbResult(0, "", "") // no "package:" line -- unparseable
                else -> AdbResult(1, "", "should not be called: $args")
            }
        }
        val controller = DeployController(fake, fakeApkPath)

        val report = controller.deploy("192.168.15.13:5555")

        assertFalse(report.overallSuccess)
        assertEquals(4, report.steps.size)
        assertTrue(report.steps.last() is DeployStepResult.Failure)
    }

    @Test
    fun `truncated dd read for a patch check is reported as failure without crashing`() {
        val fake = FakeAdbRunner { args ->
            when {
                args == listOf("connect", "192.168.15.13:5555") ->
                    AdbResult(0, "connected to 192.168.15.13:5555\n", "")
                args == listOf("install", "-r", fakeApkPath) ->
                    AdbResult(0, "Performing Streamed Install\nSuccess\n", "")
                args == listOf("shell", "am", "force-stop", "cn.upus.app.upprinting") ->
                    AdbResult(0, "", "")
                args == listOf("shell", "pm", "path", "cn.upus.app.upprinting") ->
                    AdbResult(0, "package:$fakePackageDir/base.apk\n", "")
                args.size == 2 && args[0] == "shell" && args[1].contains("skip=90350") ->
                    AdbResult(0, "00\n", "") // truncated -- expected 2 bytes, got 1
                args.size == 2 && args[0] == "shell" && args[1].contains("skip=75988") ->
                    AdbResult(0, "00 20 00 bf\n", "")
                else -> AdbResult(1, "", "unexpected call: $args")
            }
        }
        val controller = DeployController(fake, fakeApkPath)

        val report = controller.deploy("192.168.15.13:5555")

        assertFalse(report.overallSuccess)
        // 3 setup successes + 2 loop iterations (one failure for the truncated read, one success)
        assertEquals(5, report.steps.size)
        val truncatedFailure = report.steps[3] as DeployStepResult.Failure
        assertTrue(truncatedFailure.message.contains("JNI_OnLoad crash bypass"))
        assertTrue(report.steps[4] is DeployStepResult.Success)
    }
}
