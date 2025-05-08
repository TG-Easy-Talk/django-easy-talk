console.log('In main.js!');

let usernameInput = document.querySelector('#username');
let btnJoin = document.querySelector('#btn-join');

let username;
let webSocket;
let mapPeers = {};

function webSocketOnMessage(event) {
    let parsedData = JSON.parse(event.data);
    let peerUsername = parsedData.peer;
    let action = parsedData.action;

    if (username === peerUsername) {
        return;
    }

    let receiver_channel_name = parsedData.message.receiver_channel_name;

    if (action === 'new-peer') {
        createOfferer(peerUsername, receiver_channel_name);
        return;
    }

    if (action === 'new-offer') {
        let offer = parsedData.message.sdp;
        createAnswerer(offer, peerUsername, receiver_channel_name);
        return;
    }

    if (action === 'new-answer') {
        let answer = parsedData.message.sdp;
        let peer = mapPeers[peerUsername][0];
        peer.setRemoteDescription(answer);
    }
}

btnJoin.addEventListener('click', () => {
    username = usernameInput.value.trim();
    if (username === '') return;

    usernameInput.value = '';
    usernameInput.disabled = true;
    usernameInput.style.visibility = 'hidden';
    btnJoin.disabled = true;
    btnJoin.style.visibility = 'hidden';

    document.querySelector('#label-username').innerText = username;

    let loc = window.location;
    let wsStart = loc.protocol === 'https:' ? 'wss://' : 'ws://';
    let endPoint = wsStart + loc.host + '/ws/';

    console.log('Connecting to', endPoint);
    webSocket = new WebSocket(endPoint);

    webSocket.addEventListener('open', () => {
        console.log('WebSocket opened');
        sendSignal('new-peer', {});
    });

    webSocket.addEventListener('message', webSocketOnMessage);
    webSocket.addEventListener('close', () => console.log('WebSocket closed'));
    webSocket.addEventListener('error', e => console.error('WebSocket error', e));
});

let localStream = new MediaStream();
const constraints = {video: true, audio: true};
const localVideo = document.querySelector('#local-video');
const btnToggleAudio = document.querySelector('#btn-toggle-audio');
const btnToggleVideo = document.querySelector('#btn-toggle-video');

navigator.mediaDevices.getUserMedia(constraints)
    .then(stream => {
        console.log('Got MediaStream', stream);
        localStream = stream;
        localVideo.srcObject = stream;
        localVideo.muted = true;

        let audioTrack = stream.getAudioTracks()[0];
        let videoTrack = stream.getVideoTracks()[0];

        audioTrack.enabled = true;
        videoTrack.enabled = true;

        btnToggleAudio.addEventListener('click', () => {
            audioTrack.enabled = !audioTrack.enabled;
            btnToggleAudio.innerText = audioTrack.enabled ? 'Mute' : 'Unmute';
        });

        btnToggleVideo.addEventListener('click', () => {
            videoTrack.enabled = !videoTrack.enabled;
            btnToggleVideo.innerText = videoTrack.enabled ? 'Stop Video' : 'Start Video';
        });
    })
    .catch(err => console.error('Error getting MediaStream', err));

const btnSendMsg = document.querySelector('#btn-send-msg');
const messageList = document.querySelector('#message-list');
const messageInput = document.querySelector('#msg');

function sendMsgOnClick() {

    var message = messageInput.value

    var li = document.createElement('li');
    li.appendChild(document.createTextNode("me: " + message));
    messageList.appendChild(li);

    var dataChannels = getDataChannels();

    message = username + ": " + message;

    for(index in dataChannels) {
        dataChannels[index].send(message);

    }

    messageInput.value = '';
}

btnSendMsg.addEventListener('click', sendMsgOnClick)

function getDataChannels() {
    var dataChannels = [];

    for(peerUsername in mapPeers) {
        var dataChannel = mapPeers[peerUsername][1];
        dataChannels.push(dataChannel);
    }

  return dataChannels; // Agora retorna o array
}

function sendSignal(action, message) {
    webSocket.send(JSON.stringify({
        peer: username,
        action: action,
        message: message
    }));
}

function createOfferer(peerUsername, receiver_channel_name) {
    const peer = new RTCPeerConnection();

    // 1) Adiciona tracks locais
    addLocalTracks(peer, localStream);

    // 2) Prepara vídeo remoto e listener de tracks
    const remoteVideo = createVideo(peerUsername);
    setOnTrack(peer, remoteVideo);

    // 3) Gera e envia offer após ICE gathering final
    peer.addEventListener('icecandidate', event => {
        if (!event.candidate) {
            sendSignal('new-offer', {
                sdp: peer.localDescription,
                receiver_channel_name
            });
        }
    });

    peer.createOffer()
        .then(offer => peer.setLocalDescription(offer))
        .catch(console.error);

    // 4) Data channel
    const dc = peer.createDataChannel('channel');
    dc.addEventListener('open', () => console.log('Data channel opened'));
    dc.addEventListener('message', dcOnMessage);

    // 5) Mapeia peer + canal
    mapPeers[peerUsername] = [peer, dc];

    // 6) Cleanup de desconexões
    peer.addEventListener('iceconnectionstatechange', () => {
        let state = peer.iceConnectionState;
        if (['failed', 'disconnected', 'closed'].includes(state)) {
            delete mapPeers[peerUsername];
            if (state !== 'closed') peer.close();
            removeVideo(remoteVideo);
        }
    });
}

function createAnswerer(offer, peerUsername, receiver_channel_name) {
    const peer = new RTCPeerConnection();

    // 1) Adiciona tracks locais
    addLocalTracks(peer, localStream);

    // 2) Prepara vídeo remoto e listener de tracks
    const remoteVideo = createVideo(peerUsername);
    setOnTrack(peer, remoteVideo);

    // 3) Data channel handler
    peer.addEventListener('datachannel', e => {
        const dc = e.channel;
        dc.addEventListener('open', () => console.log('Data channel opened'));
        dc.addEventListener('message', dcOnMessage);
        mapPeers[peerUsername] = [peer, dc];
    });

    // 4) Cleanup de estados de ICE
    peer.addEventListener('iceconnectionstatechange', () => {
        let state = peer.iceConnectionState;
        if (['failed', 'disconnected', 'closed'].includes(state)) {
            delete mapPeers[peerUsername];
            if (state !== 'closed') peer.close();
            removeVideo(remoteVideo);
        }
    });

    // 5) Gera e envia answer após ICE gathering final
    peer.addEventListener('icecandidate', event => {
        if (!event.candidate) {
            sendSignal('new-answer', {
                sdp: peer.localDescription,
                receiver_channel_name
            });
        }
    });

    // 6) Aplica offer e cria answer
    peer.setRemoteDescription(offer)
        .then(() => peer.createAnswer())
        .then(ans => peer.setLocalDescription(ans))
        .catch(console.error);
}

function addLocalTracks(peer, stream) {
    stream.getTracks().forEach(track => peer.addTrack(track, stream));
}

function dcOnMessage(event) {
    let li = document.createElement('li');
    li.textContent = event.data;
    messageList.appendChild(li);
}

function createVideo(peerUsername) {
    let container = document.querySelector('#video-container');
    let wrapper = document.createElement('div');
    let video = document.createElement('video');

    video.id = `${peerUsername}-video`;
    video.autoplay = true;
    video.playsInline = true;

    wrapper.appendChild(video);
    container.appendChild(wrapper);
    return video;
}

function setOnTrack(peer, remoteVideo) {
    let remoteStream = new MediaStream();
    remoteVideo.srcObject = remoteStream;

    peer.addEventListener('track', event => {
        remoteStream.addTrack(event.track);
    });
}

function removeVideo(remoteVideo) {
    let wrapper = remoteVideo.parentNode;
    wrapper.parentNode.removeChild(wrapper);
}
