package com.dragx.deployer

import java.io.File
import java.io.InputStream

object AssetApkExtractor {
    fun extract(assetStream: InputStream, destination: File): File {
        destination.outputStream().use { output ->
            assetStream.copyTo(output)
        }
        return destination
    }
}
