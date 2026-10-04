// emscripten renamed allocateUTF8 to stringToNewUTF8 (3.1.35+); support both
function kert_c_string(s) {
    return (typeof stringToNewUTF8 === "function") ? stringToNewUTF8(s) : allocateUTF8(s);
}

// Qt (qwasmopenglcontext.cpp) asks for a multisampled (antialias: true) WebGL canvas, but it only copies the
// window images it painted itself onto it: multisampling adds nothing there and makes every frame of a
// full-window, device-pixel canvas (5120 x 2466 on a large Retina screen) slow to produce, so hover and
// animations stutter (docs/web-render-cost-spec.md). Ask for a plain one instead.
if (typeof OffscreenCanvas !== "undefined") {
    var kert_get_context = OffscreenCanvas.prototype.getContext;
    OffscreenCanvas.prototype.getContext = function (type, attributes) {
        if (/webgl/.test(type) && attributes) attributes.antialias = false;
        return kert_get_context.call(this, type, attributes);
    };
}

// The page starts Python with a {cmd: "py"} message to this (the main program's) worker.
function kert_handle_message(e, original) {
    if (e.data.cmd == "py") {
        try {
            _PyRun_SimpleString(kert_c_string(e.data.payload));
            // let Qt schedule the timers and posted events this Python started (main.c kert_wake_qt)
            _kert_wake_qt();
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
