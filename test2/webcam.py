import argparse
import asyncio
from http.client import HTTPException
import json
import logging
import os
import platform
import ssl

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay, MediaBlackhole, MediaRecorder
from aiortc.rtcrtpsender import RTCRtpSender

ROOT = os.path.dirname(__file__)


relay = None
webcam = None


def create_local_tracks(play_from, decode):
    global relay, webcam

    if play_from:
        player = MediaPlayer(play_from, decode=decode)
        return player.audio, player.video
    else:
        options = {"framerate": "30", "video_size": "640x480"}
        if relay is None:
            if platform.system() == "Darwin":
                webcam = MediaPlayer(
                    "default:none", format="avfoundation", options=options
                )
            elif platform.system() == "Windows":
                webcam = MediaPlayer(
                    "video=Integrated Camera", format="dshow", options=options
                )
            else:
                webcam = MediaPlayer("/dev/video0", format="v4l2", options=options)
            relay = MediaRelay()
        return None, relay.subscribe(webcam.video)


def force_codec(pc, sender, forced_codec):
    kind = forced_codec.split("/")[0]
    codecs = RTCRtpSender.getCapabilities(kind).codecs
    transceiver = next(t for t in pc.getTransceivers() if t.sender == sender)
    transceiver.setCodecPreferences(
        [codec for codec in codecs if codec.mimeType == forced_codec]
    )


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def get_offer(request):
    global web_offer_session_desc
    if web_offer_session_desc is not None:
        print("get_offer")
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                web_offer_session_desc
            ),
        )
    else:
        return web.Response(status=404, text="Not Found")


async def set_offer(request):
    global web_offer_session_desc
    params = await request.json()
    web_offer_session_desc = {
        "sdp": params["sdp"],
        "type": params["type"]
    }
    while remote_answer_session_desc is None:
        await asyncio.sleep(1)

    print("set_offer")
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            remote_answer_session_desc
        ),
    )    


async def set_stream(request):
    global web_offer_session_desc, remote_answer_session_desc
    params = await request.json()
    remote_answer_session_desc = {
        "sdp": params["sdp"],
        "type": params["type"]
    }

    if web_offer_session_desc is not None:
        print("get_anser")
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                web_offer_session_desc
            ),
        )
    else:
        return web.Response(status=404, text="Not Found")


pcs = set()
pc = None
web_offer_session_desc = None
remote_answer_session_desc = None


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC webcam demo")
    parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
    parser.add_argument("--play-from", help="Read the media from a file and sent it.")
    parser.add_argument(
        "--play-without-decoding",
        help=(
            "Read the media without decoding it (experimental). "
            "For now it only works with an MPEGTS container with only H.264 video."
        ),
        action="store_true",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    parser.add_argument(
        "--audio-codec", help="Force a specific audio codec (e.g. audio/opus)"
    )
    parser.add_argument(
        "--video-codec", help="Force a specific video codec (e.g. video/H264)"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", set_offer)
    app.router.add_get("/offer", get_offer)
    app.router.add_post("/stream", set_stream)
    web.run_app(app, host=args.host, port=args.port, ssl_context=ssl_context)