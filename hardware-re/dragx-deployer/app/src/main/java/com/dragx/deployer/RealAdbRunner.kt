package com.dragx.deployer

import java.util.concurrent.Executors

class RealAdbRunner(private val adbBinaryPath: String) : AdbRunner {
    override fun run(args: List<String>): AdbResult {
        val command = listOf(adbBinaryPath) + args
        val process = ProcessBuilder(command)
            .redirectErrorStream(false)
            .start()

        val executor = Executors.newFixedThreadPool(2)
        val stdoutFuture = executor.submit<String> { process.inputStream.bufferedReader().readText() }
        val stderrFuture = executor.submit<String> { process.errorStream.bufferedReader().readText() }

        val exitCode = process.waitFor()
        val stdout = stdoutFuture.get()
        val stderr = stderrFuture.get()
        executor.shutdown()

        return AdbResult(exitCode, stdout, stderr)
    }
}
