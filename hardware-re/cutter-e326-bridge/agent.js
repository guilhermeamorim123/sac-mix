rpc.exports = {
    gethandshake: function (nonceStr) {
        return new Promise(function (resolve, reject) {
            Java.perform(function () {
                try {
                    var JniUtils = Java.use('com.cut.cutjni.JniUtils');
                    var nonce = parseInt(nonceStr, 10);
                    var result = JniUtils.getHandshake(nonce);
                    var hex = "";
                    for (var i = 0; i < result.length; i++) {
                        var b = result[i] & 0xff;
                        hex += ("0" + b.toString(16)).slice(-2);
                    }
                    resolve(hex);
                } catch (e) {
                    reject(new Error("" + e));
                }
            });
        });
    }
};
