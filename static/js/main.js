console.log('In main.js!');

var usernameInput = document.querySelector('#username');
var btnJoin = document.querySelector('#btn-join');

var username;
var webSocket;

function webSocketOnMessage(event) {
    var parsedData = JSON.parse(event.data);
    var message = parsedData.message;
}

btnJoin.addEventListener('click', () => {
    username = usernameInput.value;

    console.log('username: ', username);

    if (username == '') {
        return;
    }

    usernameInput.value = '';
    usernameInput.disabled = true;
    usernameInput.style.visibility = 'hidden';

    btnJoin.disabled = true;
    btnJoin.style.visibility = 'hidden';

    var labelUsername = document.querySelector('#label-username');
    labelUsername.innerHTML = username;

    var loc = window.location;
    var wsStart = 'ws://';

    if (loc.protocol === 'https:') {
        wsStart = 'wss://';
    }

    var endPoint = wsStart + loc.host + '/ws';

    console.log('endPoint: ', endPoint);
});
