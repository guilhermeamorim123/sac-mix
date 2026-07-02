package com.dragx.deployer

interface AdbRunner {
    fun run(args: List<String>): AdbResult
}
