package cn.upus.app.upprinting.dragx.ui.activity;

import androidx.core.content.FileProvider;

/**
 * Exists purely so this app's self-update FileProvider registration has
 * its own distinct implementation class -- every other FileProvider
 * already declared in this app's manifest (the plain "fileprovider", the
 * blankj "utilcode.fileprovider", the zbar/QR one, the AgentWeb one, the
 * Bugly one) uses its own unique subclass. Reusing the bare
 * androidx.core.content.FileProvider class for a second provider entry
 * (which is what the first attempt did) caused Android's provider
 * resolution to route requests to the WRONG registered instance,
 * confirmed live (2026-07-21, logcat): PackageInstaller's query landed
 * on the FIRST-declared FileProvider ("cn.upus.app.upprinting.dragx.
 * fileprovider") instead of ours, throwing a SecurityException. A
 * distinct class name -- even with zero added behavior -- is the fix.
 */
public class SelfUpdateFileProvider extends FileProvider {
}
