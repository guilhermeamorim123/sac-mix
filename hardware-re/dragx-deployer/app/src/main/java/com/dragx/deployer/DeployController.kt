package com.dragx.deployer

sealed class DeployStepResult {
    data class Success(val message: String) : DeployStepResult()
    data class Failure(val message: String) : DeployStepResult()
}

data class DeployReport(
    val steps: List<DeployStepResult>,
    val overallSuccess: Boolean
)

class DeployController(
    private val adb: AdbRunner,
    private val apkPath: String,
    private val targetPackage: String = "cn.upus.app.upprinting",
    private val nativeLibRelativePath: String = "lib/arm/libnewcutjni.so"
) {

    fun deploy(ipPort: String): DeployReport {
        val steps = mutableListOf<DeployStepResult>()

        val connectResult = adb.run(listOf("connect", ipPort))
        if (!AdbOutputParser.isConnectSuccess(connectResult)) {
            steps += DeployStepResult.Failure(
                "Não foi possível conectar em $ipPort: ${connectResult.stdout}${connectResult.stderr}"
            )
            return DeployReport(steps, overallSuccess = false)
        }
        steps += DeployStepResult.Success("Conectado a $ipPort")

        val installResult = adb.run(listOf("install", "-r", apkPath))
        if (!AdbOutputParser.isInstallSuccess(installResult)) {
            steps += DeployStepResult.Failure(
                "Falha ao instalar: ${installResult.stdout}${installResult.stderr}"
            )
            return DeployReport(steps, overallSuccess = false)
        }
        steps += DeployStepResult.Success("DragX instalado")

        adb.run(listOf("shell", "am", "force-stop", targetPackage))
        steps += DeployStepResult.Success("Processo antigo finalizado")

        val pmPathResult = adb.run(listOf("shell", "pm", "path", targetPackage))
        val packageDir = AdbOutputParser.parsePackageDir(pmPathResult.stdout)
        if (packageDir == null) {
            steps += DeployStepResult.Failure(
                "Não achei o caminho do pacote instalado: ${pmPathResult.stdout}${pmPathResult.stderr}"
            )
            return DeployReport(steps, overallSuccess = false)
        }

        val libPath = "$packageDir/$nativeLibRelativePath"
        var allPatchesOk = true
        for (check in PatchVerifier.ALL_CHECKS) {
            val actualBytes = readRemoteBytes(libPath, check.offset, check.expectedBytes.size)
            if (actualBytes == null) {
                steps += DeployStepResult.Failure(
                    "Não consegui ler bytes de $libPath no offset ${check.offset} para checar '${check.name}'"
                )
                allPatchesOk = false
                continue
            }
            val result = PatchVerifier.verify(check, actualBytes)
            if (result.passed) {
                steps += DeployStepResult.Success("${check.name}: OK")
            } else {
                steps += DeployStepResult.Failure(
                    "${check.name}: FALHOU (esperado ${result.expectedHex}, encontrado ${result.actualHex})"
                )
                allPatchesOk = false
            }
        }

        return DeployReport(steps, overallSuccess = allPatchesOk)
    }

    private fun readRemoteBytes(remotePath: String, offset: Long, count: Int): ByteArray? {
        val remoteCommand = "dd if=$remotePath bs=1 skip=$offset count=$count 2>/dev/null | od -An -tx1"
        val ddResult = adb.run(listOf("shell", remoteCommand))
        val hexTokens = ddResult.stdout.trim().split(Regex("\\s+")).filter { it.isNotBlank() }
        if (hexTokens.size != count) return null
        return try {
            ByteArray(hexTokens.size) { i -> hexTokens[i].toInt(16).toByte() }
        } catch (e: NumberFormatException) {
            null
        }
    }
}
