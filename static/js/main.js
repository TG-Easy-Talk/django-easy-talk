console.log('In main.js!');

var usernameInput = document.querySelector('#username');
var btnJoin = document.querySelector('#btn-join');

var username;
var webSocket;
var mapPeers = {};


function webSocketOnMessage(event) {
    var parsedData = JSON.parse(event.data);
    var peerUsername = parsedData['peer'];
    var action = parsedData['action'];

    if (username === peerUsername) {
        return;
    }

    var receiver_channel_name = parsedData['message']['receiver_channel_name'];


    if (action === 'new-peer') {
        createOfferer(peerUsername, receiver_channel_name);

        return
    }

    if (action === 'new-offer') {
        var offer = parsedData['message']['sdp'];

        createAnswerer(peerUsername, offer, receiver_channel_name);
        return;
    }

    if (action === 'new-answer') {
        var answer = parsedData['message']['sdp'];
        var peer = mapPeers[peerUsername][0];
        peer.setRemoteDescription(answer);
    }
}

btnJoin.addEventListener('click', () => {
    username = usernameInput.value;

    console.log('username: ', username);

    if (username === '') {
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

    var endPoint = wsStart + loc.host + '/ws/';

    console.log('endPoint: ', endPoint);

    webSocket = new WebSocket(endPoint);

    webSocket.addEventListener('open', (e) => {
        console.log('WebSocket connection opened');

        sendSignal('new-peer', {});

    })
    webSocket.addEventListener('message', (e) => {
        webSocketOnMessage(e);
    });
    webSocket.addEventListener('close', (e) => {
        console.log('WebSocket connection closed');
    });
    webSocket.addEventListener('error', (e) => {
        console.log('WebSocket error: ', e);
    })
});


var localStream = new MediaStream();

const constraint = {
    'video': true,
    'audio': true
}

const localVideo = document.querySelector('#local-video');
const btnToggleAudio = document.querySelector('#btn-toggle-audio');
const btnToggleVideo = document.querySelector('#btn-toggle-video');


var userMedia = navigator.mediaDevices.getUserMedia(constraint)
    .then(stream => {
        console.log('Got MediaStream: ', stream);
        localStream = stream;
        localVideo.srcObject = localStream;
        localVideo.muted = true;

        var audioTracks = localStream.getAudioTracks();
        var videoTracks = localStream.getVideoTracks();

        audioTracks[0].enabled = true;
        videoTracks[0].enabled = true;

        btnToggleAudio.addEventListener('click', () => {
            audioTracks[0].enabled = !audioTracks[0].enabled;
            if (audioTracks[0].enabled) {
                btnToggleAudio.innerHTML = 'Mute';
                return;
            }

            btnToggleAudio.innerHTML = 'Unmute';
        });

        btnToggleVideo.addEventListener('click', () => {
            videoTracks[0].enabled = !videoTracks[0].enabled;
            if (videoTracks[0].enabled) {
                btnToggleVideo.innerHTML = 'Stop Video';
                return;
            }

            btnToggleVideo.innerHTML = 'Start Video';
        });

    })
    .catch(err => {
        console.log('Error getting MediaStream: ', err);
    });

function sendSignal(action, message) {
    var jsonStr = JSON.stringify({
        'peer': username,
        'action': action,
        'message': message
    })

    webSocket.send(jsonStr);
}

function createOfferer(peerUsername, receiver_channel_name) {
    var peer = new RTCPeerConnection(null)

    addLocalTracks(peer, localStream);

    var dc = peer.createDataChannel('channel')
    dc.addEventListener('open', () => {
        console.log('Data channel opened');
    })
    dc.addEventListener('message', dcOnMessage)

    var remoteVideo = createVideo(peerUsername);
    setOnTrack(peer, peerUsername);

    mapPeers[peerUsername] = [peer, dc]
    peer.addEventListener('iceconnectionstatechange', (event) => {
        var iceConnectionState = peer.iceConnectionState;

        if (iceConnectionState === 'failed' || iceConnectionState === 'disconnected' || iceConnectionState === 'closed') {
            delete mapPeers[peerUsername];

            if (iceConnectionState !== 'closed') {
                peer.close();
            }

            removeVideo(remoteVideo);
        }
    })

    peer.addEventListener('icecandidate', (event) => {
        if (event.candidate) {
            console.log('New ice candidate: ', JSON.stringify(event.candidate));
            return;
        }

        sendSignal('new-offer', {
            'sdp': peer.localDescription,
            'receiver_channel_name': receiver_channel_name
        })

        // 1. Cria offer e seta
        peer.createOffer()
            .then(offer => peer.setLocalDescription(offer))
            .then(() => {
                console.log('Offer created: ', peer.localDescription);

                // 2. Aguarda ICE gathering completo
                peer.addEventListener('icecandidate', event => {
                    if (!event.candidate) {
                        // envio só após gathering final
                        sendSignal('new-offer', {
                            sdp: peer.localDescription,
                            receiver_channel_name: receiver_channel_name
                        });
                    }
                });
            });
    })
}

function createAnswerer(offer, peerUsername, receiver_channel_name) {
    var peer = new RTCPeerConnection(null)

    addLocalTracks(peer, localStream);

    var remoteVideo = createVideo(peerUsername);
    setOnTrack(peer, peerUsername);

    peer.addEventListener('datachannel', e => {
        peer.dc = e.channel;
        peer.dc.addEventListener('open', () => {
            console.log('Data channel opened');
        })
        peer.dc.addEventListener('message', dcOnMessage)
        mapPeers[peerUsername] = [peer, dc]

    })

    peer.addEventListener('iceconnectionstatechange', (event) => {
        var iceConnectionState = peer.iceConnectionState;

        if (iceConnectionState === 'failed' || iceConnectionState === 'disconnected' || iceConnectionState === 'closed') {
            delete mapPeers[peerUsername];

            if (iceConnectionState !== 'closed') {
                peer.close();
            }

            removeVideo(remoteVideo);
        }
    })

    peer.addEventListener('icecandidate', (event) => {
        if (event.candidate) {
            console.log('New ice candidate: ', JSON.stringify(event.localDescription));
            return;
        }

        sendSignal('new-answer', {
            'sdp': peer.localDescription,
            'receiver_channel_name': receiver_channel_name
        })
    })

    peer.setRemoteDescription(offer)
        .then(() => {
            console.log('Set remote description set successfully for: ', peerUsername);
            return peer.createAnswer();
        })
        .then(answer => {
            console.log('Answer created: ', answer);
            return peer.setLocalDescription(answer);
        })

}

function addLocalTracks(peer) {
    localStream.getTracks().forEach(track => {
        peer.addTrack(track, localStream);
    })
    return;
}

var messageList = document.querySelector('#message-list');

function dcOnMessage(event) {
    var message = event.data;

    var li = document.createElement('li');
    li.appendChild(document.createTextNode(message));
    messageList.appendChild(li);
}

function createVideo(peerUsername) {
    var videoContainer = document.querySelector('#video-container');

    var remoteVideo = document.createElement('video');

    remoteVideo.id = peerUsername + '-video';
    remoteVideo.autoplay = true;
    remoteVideo.playsInline = true;

    var videoWrapper = document.createElement('div');

    videoContainer.appendChild(videoWrapper);

    videoWrapper.appendChild(remoteVideo);

    return remoteVideo;
}

function setOnTrack(peer, remoteVideo) {
    var remoteStream = new MediaStream();

    remoteVideo.srcObject = remoteStream;

    peer.addEventListener('track', async (event) => {
        remoteStream.addTrack(event.track, remoteStream);
    });
}

function removeVideo(remoteVideo) {
    var videoWrapper = remoteVideo.parentNode;
    videoWrapper.parentNode.removeChild(videoWrapper);
}
