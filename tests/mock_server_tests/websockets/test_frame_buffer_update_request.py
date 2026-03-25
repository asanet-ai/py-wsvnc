import asyncio
from struct import pack

from websockets import WebSocketServerProtocol

from tests.conftest import MockVNCBaseServer
from wsvnc.vnc.vnc_client import WSVNCClient


class MockVNCServer(MockVNCBaseServer):
    def __init__(self):
        super().__init__()
        self.framebuffer_request_count = 0
        self.frame_sent = asyncio.Event()

    async def recv_frame_buffer_update_request(
        self, websocket: WebSocketServerProtocol
    ):
        fbur = await websocket.recv()
        self.framebuffer_request_count += 1
        assert fbur[0] == 3
        assert fbur[1] == 0
        assert fbur[2:4] == pack(">H", 0)
        assert fbur[4:6] == pack(">H", 0)

    async def frame_buffer_update(self, websocket: WebSocketServerProtocol):
        header = pack(">bxHHHHHI", 0, 1, 0, 0, 1, 1, 0)
        pixel_data = b"\x00\x11\x22\xff"
        await websocket.send(header + pixel_data)
        self.frame_sent.set()

    async def handler(self, websocket):
        self.clients.add(websocket)
        try:
            await self.handshake(websocket)
            await self.recv_frame_buffer_update_request(websocket)
            await self.frame_buffer_update(websocket)
        finally:
            self.clients.remove(websocket)


async def main():
    # start the server
    server = MockVNCServer()
    await asyncio.sleep(1)

    # start the client (using the VNCSecurity scheme)
    c = WSVNCClient(ticket_url="ws://localhost:8765")

    # save the image from the client to a file for this test
    # should be some random pixels
    await asyncio.sleep(1)  # wait for image to process

    # update the screen
    c.update_screen()

    # close server & client
    c.close()
    server.close()


def test():
    asyncio.run(main())


async def main_wait_for_frame():
    server = MockVNCServer()
    await asyncio.sleep(1)

    c = WSVNCClient(ticket_url="ws://localhost:8765")

    try:
        await asyncio.to_thread(c.update_screen, wait_for_frame=True, timeout_sec=2)
        await asyncio.wait_for(server.frame_sent.wait(), timeout=2)
        assert c._rfb_client.frame_count >= 1
        assert c.get_screen() is not None
    finally:
        c.close()
        server.close()


def test_wait_for_frame():
    asyncio.run(main_wait_for_frame())
