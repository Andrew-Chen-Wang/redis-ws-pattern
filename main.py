import asyncio
import contextvars
from typing import TypedDict
from uuid import uuid4

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError
import orjson
from fastapi import FastAPI, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/{chat_id}")
async def get(request: Request, chat_id: int):
    return templates.TemplateResponse("index.html", {"request": request, "id": chat_id})


r = redis.Redis()


class RedisConnection:
    def __init__(self):
        self.reader_task: asyncio.Task | None = None

    async def start(self):
        async with r.pubsub() as pubsub:
            await pubsub.psubscribe("channel:*")
            self.reader_task = asyncio.create_task(reader(pubsub))
            await self.reader_task

    async def close(self):
        if self.reader_task is not None:
            self.reader_task.cancel("Shutting down")
        await r.close()


conn = RedisConnection()


@app.on_event("startup")
async def startup():
    asyncio.create_task(conn.start())


@app.on_event("shutdown")
async def shutdown():
    await conn.close()


# Chat ID -> Reader ID -> WSReader
readers: contextvars.ContextVar[dict[int, dict[str, "WSReader"]]] = (
    contextvars.ContextVar("readers", default={})
)


class Message(TypedDict):
    type: str  # pmessage
    pattern: bytes  # b"channel:*"
    channel: bytes  # b"channel:1"
    data: bytes  # b"Hello"


async def reader(channel: redis.client.PubSub):
    global readers
    # noinspection PyBroadException
    try:
        while True:
            message: Message = await channel.get_message(ignore_subscribe_messages=True)
            if message is not None:
                wsr = readers.get().get(
                    int(message["channel"].decode().split(":")[1]), {}
                ).items()
                data: dict = orjson.loads(message["data"])
                reader_id = data.pop("id")
                [w.messages.append(data) for k, w in wsr if k != reader_id]
    except RedisConnectionError:
        pass
    finally:
        pass


class WSReader:
    def __init__(self, websocket: WebSocket, chat_id: int):
        self.websocket = websocket
        self.chat_id = chat_id
        self.messages: list[dict] = []

    async def handle(self, message: dict):
        await self.websocket.send_text(message["data"])

    async def listen(self):
        try:
            while True:
                if self.messages:
                    await self.handle(self.messages.pop(0))
                await asyncio.sleep(0.1)
        finally:
            pass


@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    await websocket.accept()
    _id = str(uuid4())
    readers.get().setdefault(chat_id, {})[_id] = _reader = WSReader(websocket, chat_id)
    t = asyncio.create_task(_reader.listen())
    try:
        while True:
            data = await websocket.receive_text()
            await r.publish(f"channel:{chat_id}", orjson.dumps({"data": data, "id": _id}))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            readers.get()[chat_id].pop(_id)
        except KeyError:
            pass
        t.cancel()
