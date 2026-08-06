Java.perform(function () {
    function callOnce(nonce) {
        try {
            var JniUtils = Java.use('com.cut.cutjni.JniUtils');
            var result = JniUtils.getHandshake(nonce);
            var hex = "";
            var ascii = "";
            for (var i = 0; i < result.length; i++) {
                var b = result[i] & 0xff;
                hex += ("0" + b.toString(16)).slice(-2);
                ascii += (b >= 32 && b < 127) ? String.fromCharCode(b) : ".";
            }
            send("nonce=" + nonce + " hex=" + hex + " ascii=" + ascii);
        } catch (e) {
            send("nonce=" + nonce + " ERROR: " + e);
        }
    }
    callOnce(123456);
    callOnce(123456);
    callOnce(1);
    callOnce(999999999);
    callOnce(123457);
});
