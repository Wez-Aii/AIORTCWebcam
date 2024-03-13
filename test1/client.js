var pc = null;

function negotiate() {
    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });
    return fetch('/offer').then((response) => {
        console.log("response",response)
        return response.json();
    }).then((offer) => {
        console.log("offer",offer)
        pc.setRemoteDescription(offer);
        return pc.createAnswer().then((answer) => {
            return pc.setLocalDescription(answer)
        // }).then(() => {
        //     return new Promise((resolve) => {
        //         if (pc.iceGatheringState === 'complete') {
        //             resolve();
        //         } else {
        //             const checkState = () => {
        //                 if (pc.iceGatheringState === 'complete') {
        //                     pc.removeEventListener('icegatheringstatechange', checkState);
        //                     resolve();
        //                 }
        //             }
        //             pc.addEventListener('icegatheringstatechange', checkState);
        //         }
        //     })
        }).then(() => {
            var answer = pc.localDescription;
            return fetch('/answer', {
                body: JSON.stringify({
                    sdp: answer.sdp,
                    type: answer.type,
                }),
                headers: {
                    'Content-Type': 'application/json'
                },
                method: 'POST'
            });
        }).then((response) => {
                console.log("response",response)
                console.log("pc",pc)
                return pc;
            })
    }).catch((e) => {
        alert(e);
    });
}

function start() {
    var config = {
        sdpSemantics: 'unified-plan'
    };

    if (document.getElementById('use-stun').checked) {
        config.iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];
    }

    pc = new RTCPeerConnection(config);

    // connect audio / video
    pc.addEventListener('track', (evt) => {
        console.log("get track -", evt);
        if (evt.track.kind == 'video') {
            document.getElementById('video').srcObject = evt.streams[0];
        } else {
            document.getElementById('audio').srcObject = evt.streams[0];
        }
    });

    document.getElementById('start').style.display = 'none';
    negotiate();
    document.getElementById('stop').style.display = 'inline-block';
}

function stop() {
    document.getElementById('stop').style.display = 'none';

    // close peer connection
    setTimeout(() => {
        pc.close();
    }, 500);
}