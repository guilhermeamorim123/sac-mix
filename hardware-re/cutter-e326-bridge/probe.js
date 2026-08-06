Java.perform(function () {
    try {
        send("java.perform start");
        var JniUtils = Java.use('com.cut.cutjni.JniUtils');
        send("JniUtils class resolved");
        var nonce = 123456;
        var result = JniUtils.getHandshake(nonce);
        send("getHandshake returned, length=" + (result ? result.length : "null"));
        if (result) {
            var hex = "";
            for (var i = 0; i < result.length; i++) {
                var b = result[i] & 0xff;
                hex += ("0" + b.toString(16)).slice(-2);
            }
            send("HEX:" + hex);
        }
    } catch (e) {
        send("ERROR: " + e + "\n" + e.stack);
    }
});
