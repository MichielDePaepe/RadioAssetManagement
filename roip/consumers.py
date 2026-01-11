# roip/consumers.py

from __future__ import annotations

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class LiveTxConsumer(AsyncJsonWebsocketConsumer):
    group_name = "live_tx"

    async def connect(self) -> None:
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def tx_event(self, event) -> None:
        # event = {"type": "tx.event", "data": {...}}
        await self.send_json(event["data"])