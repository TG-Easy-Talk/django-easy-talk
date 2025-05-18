// import AgoraRTC from "agora-rtc-sdk-ng";

const APP_ID = '5c894664474548608bf0dfc4cd6c5c1e';
const TOKEN = sessionStorage.getItem('token')
    || '007eJxTYAje0BT30vv91igV0T1mN/tz5CskNP+6bLaUWfyAax/7py8KDKbJFpYmZmYmJuYmpiYWZgYWSWkGKWnJJskpZsmmyYapuxS0MhoCGRkS5HlYGRkgEMRnYchNzMxjYAAABEwdnQ==';
const CHANNEL = sessionStorage.getItem('room') || 'main';
let UID = sessionStorage.getItem('UID');
const NAME = sessionStorage.getItem('name');

const client = AgoraRTC.createClient({mode: 'rtc', codec: 'vp8'});


let localTracks = [];
let remoteUsers = {};

// Registra eventos antes do join para não perder callbacks
client.on('user-published', handleUserJoined);
client.on('user-left', handleUserLeft);

document.addEventListener('DOMContentLoaded', () => {
    // Atualiza nome da sala
    const roomNameEl = document.getElementById('room-name');
    roomNameEl && (roomNameEl.innerText = CHANNEL);

    // Anexa listeners de controle
    document.getElementById('leave-btn')?.addEventListener('click', leaveAndRemoveLocalStream);
    document.getElementById('camera-btn')?.addEventListener('click', toggleCamera);
    document.getElementById('mic-btn')?.addEventListener('click', toggleMic);

    // Inicia o fluxo principal
    joinAndDisplayLocalStream();
});

window.addEventListener('beforeunload', deleteMember);

async function joinAndDisplayLocalStream() {
    try {
        UID = await client.join(APP_ID, CHANNEL, TOKEN, UID);
    } catch (error) {
        console.error(error);
        return window.open('/', '_self');
    }

    // Cria trilhas de áudio e vídeo
    localTracks = await AgoraRTC.createMicrophoneAndCameraTracks();

    // Registra usuário no backend
    const member = await createMember();

    // Renderiza vídeo local
    const playerHTML = `
    <div class="video-container" id="user-container-${UID}">
      <div class="video-player" id="user-${UID}"></div>
      <div class="username-wrapper">
        <span class="user-name">${member.name}</span>
      </div>
    </div>`;
    document.getElementById('video-streams')?.insertAdjacentHTML('beforeend', playerHTML);
    localTracks[1].play(`user-${UID}`);

    // Publica trilhas locais
    await client.publish([localTracks[0], localTracks[1]]);
}

async function handleUserJoined(user, mediaType) {
    remoteUsers[user.uid] = user;
    await client.subscribe(user, mediaType);

    if (mediaType === 'video') {
        document.getElementById(`user-container-${user.uid}`)?.remove();
        const member = await getMember(user);
        const playerHTML = `
      <div class="video-container" id="user-container-${user.uid}">
        <div class="video-player" id="user-${user.uid}"></div>
        <div class="username-wrapper">
          <span class="user-name">${member.name}</span>
        </div>
      </div>`;
        document.getElementById('video-streams')?.insertAdjacentHTML('beforeend', playerHTML);
        user.videoTrack.play(`user-${user.uid}`);
    }

    if (mediaType === 'audio') {
        user.audioTrack.play();
    }
}

async function handleUserLeft(user) {
    delete remoteUsers[user.uid];
    document.getElementById(`user-container-${user.uid}`)?.remove();
}

async function leaveAndRemoveLocalStream() {
    localTracks.forEach(track => {
        track.stop();
        track.close();
    });
    await client.leave();
    await deleteMember();
    window.open('/', '_self');
}

async function toggleCamera(e) {
    if (localTracks[1].muted) {
        await localTracks[1].setMuted(false);
        e.target.style.backgroundColor = '#fff';
    } else {
        await localTracks[1].setMuted(true);
        e.target.style.backgroundColor = 'rgb(255, 80, 80, 1)';
    }
}

async function toggleMic(e) {
    if (localTracks[0].muted) {
        await localTracks[0].setMuted(false);
        e.target.style.backgroundColor = '#fff';
    } else {
        await localTracks[0].setMuted(true);
        e.target.style.backgroundColor = 'rgb(255, 80, 80, 1)';
    }
}

async function createMember() {
    const res = await fetch('/create_member/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: NAME, room_name: CHANNEL, UID})
    });
    return res.json();
}

async function getMember(user) {
    const res = await fetch(`/get_member/?UID=${user.uid}&room_name=${CHANNEL}`);
    return res.json();
}

async function deleteMember() {
    await fetch('/delete_member/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: NAME, room_name: CHANNEL, UID})
    });
}
