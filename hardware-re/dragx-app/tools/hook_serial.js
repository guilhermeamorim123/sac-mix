Java.perform(function () {
    function bytesToHex(bytesObj) {
        var arr = [];
        var len = bytesObj.length;
        for (var i = 0; i < len; i++) {
            var b = bytesObj[i] & 0xff;
            arr.push(("0" + b.toString(16)).slice(-2));
        }
        return arr.join(" ");
    }
    function bytesToAscii(bytesObj) {
        var s = "";
        var len = bytesObj.length;
        for (var i = 0; i < len; i++) {
            var b = bytesObj[i] & 0xff;
            s += (b >= 32 && b < 127) ? String.fromCharCode(b) : ".";
        }
        return s;
    }

    try {
        var SerialPortHelp = Java.use('b.b.a.a.j.d');

        // g(byte[]) writes raw bytes to the serial OutputStream
        SerialPortHelp.g.overload('[B').implementation = function (bArr) {
            send("[WRITE] hex=" + bytesToHex(bArr) + " ascii=" + bytesToAscii(bArr));
            var result = this.g(bArr);
            send("[WRITE] g() returned " + result);
            return result;
        };

        send("hooked SerialPortHelp.g([B) OK");
    } catch (e) {
        send("ERROR hooking g(): " + e);
    }

    try {
        var SerialPortHelpInner_c = Java.use('b.b.a.a.j.d$c');
        // can't easily hook the run() read loop internals directly since it's not a clean boundary,
        // but we can hook InputStream.read via a wrapper if needed. Instead, hook the SerialPort open.
    } catch (e) {
        send("note: " + e);
    }

    try {
        var SerialPortClass = Java.use('android.serialport.SerialPort');
        send("SerialPort class found, hooking getInputStream/getOutputStream");
    } catch (e) {
        send("SerialPort class lookup failed: " + e);
    }

    // Hook InputStream.read(byte[]) globally is too broad; instead hook FileInputStream.read since
    // SerialPort likely returns a FileInputStream/FileOutputStream wrapping the fd.
    try {
        var FileInputStream = Java.use('java.io.FileInputStream');
        FileInputStream.read.overload('[B').implementation = function (bArr) {
            var n = this.read(bArr);
            if (n > 0) {
                var sub = Java.array('byte', []);
                var arr = [];
                for (var i = 0; i < n; i++) arr.push(bArr[i]);
                var hex = arr.map(function(b){ b = b & 0xff; return ("0"+b.toString(16)).slice(-2);}).join(" ");
                var ascii = arr.map(function(b){ b = b & 0xff; return (b>=32&&b<127)?String.fromCharCode(b):"."; }).join("");
                send("[READ fis] n=" + n + " hex=" + hex + " ascii=" + ascii);
            }
            return n;
        };
        send("hooked FileInputStream.read([B) OK");
    } catch (e) {
        send("ERROR hooking FileInputStream.read: " + e);
    }

    try {
        var FileOutputStream = Java.use('java.io.FileOutputStream');
        FileOutputStream.write.overload('[B').implementation = function (bArr) {
            var arr = [];
            for (var i = 0; i < bArr.length; i++) arr.push(bArr[i]);
            var hex = arr.map(function(b){ b = b & 0xff; return ("0"+b.toString(16)).slice(-2);}).join(" ");
            var ascii = arr.map(function(b){ b = b & 0xff; return (b>=32&&b<127)?String.fromCharCode(b):"."; }).join("");
            send("[WRITE fos] hex=" + hex + " ascii=" + ascii);
            return this.write(bArr);
        };
        send("hooked FileOutputStream.write([B) OK");
    } catch (e) {
        send("ERROR hooking FileOutputStream.write: " + e);
    }
});
