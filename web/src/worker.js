// emscripten renamed allocateUTF8 to stringToNewUTF8 (3.1.35+); support both
function kert_c_string(s) {
    return (typeof stringToNewUTF8 === "function") ? stringToNewUTF8(s) : allocateUTF8(s);
}

// The page starts Python with a {cmd: "py"} message to this (the main program's) worker.
function kert_handle_message(e, original) {
    if (e.data.cmd == "py") {
        try {
            _PyRun_SimpleString(kert_c_string(e.data.payload));
        } catch (ex) {
            // never leave the page waiting with a spinner: report the failure
            postMessage({cmd: "fatal_error", msg: "Python start failed: " + ex});
            throw ex;
        }
    } else {
        original(e);
    }
}

if (typeof handleMessage === "function") {
    // emscripten 3.1.4x+: the worker re-installs its own handleMessage as self.onmessage once the module is
    // loaded, which would drop a wrapper put on self.onmessage now; wrap the function itself instead
    var kert_original_handle = handleMessage;
    handleMessage = function (e) { kert_handle_message(e, kert_original_handle); };
}
var old_msg = self.onmessage;
self.onmessage = function (e) { kert_handle_message(e, old_msg); };

function vialgluejs_write_device(data) {
    var buf = [];
    for (var i = 0; i < 32; ++i) {
        buf.push(getValue(data + i, "i8"));
    }
    postMessage({cmd: "write_device", data: buf});
}

function vialgluejs_unlock_start(data, size, width, height) {
    var buf = []
    for (var i = 0; i < size; ++i) {
        buf.push(getValue(data + i, "i8"));
    }
    postMessage({cmd: "unlock_start", data: buf, width: width, height: height});
}

var window = {};
window.open = function() {};
