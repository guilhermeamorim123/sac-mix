package com.dragx.deployer

object AdbOutputParser {

    // "adb connect" prints "connected to <ip>:<port>" on success, and
    // "already connected to <ip>:<port>" if a connection is already open --
    // both contain "connected to" as a substring, so one check covers both.
    fun isConnectSuccess(result: AdbResult): Boolean {
        return result.stdout.contains("connected to")
    }

    // "adb install" prints a final line "Success" on success.
    fun isInstallSuccess(result: AdbResult): Boolean {
        return result.stdout.trim().lines().any { it.trim() == "Success" }
    }

    // "adb shell pm path <pkg>" prints one line: "package:/data/app/<pkg>-N/base.apk"
    fun parsePackageDir(pmPathOutput: String): String? {
        val line = pmPathOutput.trim().lineSequence().firstOrNull { it.startsWith("package:") }
            ?: return null
        val apkPath = line.removePrefix("package:").trim()
        val lastSlash = apkPath.lastIndexOf('/')
        if (lastSlash <= 0) return null
        return apkPath.substring(0, lastSlash)
    }
}
