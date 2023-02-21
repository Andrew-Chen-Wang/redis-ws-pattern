const form = document.getElementById("form");
const roomId = form.dataset.room;
let ws = new WebSocket(`ws://localhost:8000/ws/${roomId}`);
function addMessage(message) {
    let messages = document.getElementById('messages');
    let messageElement = document.createElement('li');
    let content = document.createTextNode(message);
    messageElement.appendChild(content);
    messages.appendChild(messageElement);
}
ws.onmessage = function(event) {
    addMessage(event.data);
};
function sendMessage(event) {
    let input = document.getElementById("messageText")
    ws.send(input.value);
    addMessage(input.value);
    input.value = "";
    event.preventDefault();
}
form.addEventListener("submit", sendMessage);
