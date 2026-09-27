// script.js
// Connects to the Flask-SocketIO server and shows live "toast" notifications.
// This is the BROWSER-side real-time piece (separate from the raw
// socket_server.py/socket_client.py demo used for the plain Socket
// Programming college requirement).

document.addEventListener("DOMContentLoaded", function () {
    if (typeof io === "undefined") {
        return; // socket.io failed to load (e.g. no internet) - fail gracefully
    }

    const socket = io();

    socket.on("connect", function () {
        if (window.CURRENT_USER_ID) {
            socket.emit("join", { user_id: window.CURRENT_USER_ID });
        }
    });

    socket.on("notification", function (data) {
        showToast(data.message);
    });
});

function showToast(message) {
    const toast = document.getElementById("notification-toast");
    if (!toast) return;
    toast.innerText = message;
    toast.classList.remove("hidden");
    setTimeout(function () {
        toast.classList.add("hidden");
    }, 6000);
}
