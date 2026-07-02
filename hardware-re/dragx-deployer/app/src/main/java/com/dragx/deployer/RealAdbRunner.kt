package com.dragx.deployer

class RealAdbRunner(private val adbBinaryPath: String) : AdbRunner {
    override fun run(args: List<String>): AdbResult {
        val command = listOf(adbBinaryPath) + args
        val process = ProcessBuilder(command)
            .redirectErrorStream(false)
            .start()
        val stdout = process.inputStream.bufferedReader().readText()
        val stderr = process.errorStream.bufferedReader().readText()
        val exitCode = process.waitFor()
        return AdbResult(exitCode, stdout, stderr)
    }
}
