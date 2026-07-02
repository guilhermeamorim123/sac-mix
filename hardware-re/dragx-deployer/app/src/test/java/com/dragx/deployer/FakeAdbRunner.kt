package com.dragx.deployer

class FakeAdbRunner(private val responder: (List<String>) -> AdbResult) : AdbRunner {
    val callLog = mutableListOf<List<String>>()

    override fun run(args: List<String>): AdbResult {
        callLog += args
        return responder(args)
    }
}
