package com.dragx.deployer

data class AdbResult(
    val exitCode: Int,
    val stdout: String,
    val stderr: String
) {
    val succeeded: Boolean get() = exitCode == 0
}
