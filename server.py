import json
import logging
import trio
import dataclasses

from dataclasses import dataclass
from functools import partial
from trio_websocket import serve_websocket, ConnectionClosed
from typing import Dict


@dataclass
class Bus:
    lat:   float
    lng:   float
    route: str


@dataclass
class WindowBounds:
    north_lat: float
    south_lat: float
    east_lng:  float
    west_lng:  float

    def update(self, bounds: Dict):
        self.north_lat = bounds.get("north_lat")
        self.south_lat = bounds.get("south_lat")
        self.east_lng = bounds.get("east_lng")
        self.west_lng = bounds.get("west_lng")

    def is_inside(self, lat, lng):
        if lat > self.north_lat:
            return False
        if lat < self.south_lat:
            return False
        if lng > self.east_lng:
            return False
        if lng < self.west_lng:
            return False
        return True


buses = dict()
window = WindowBounds(0,0,0,0)


def make_message_to_browser(buses):
    global window
    message = {
        "msgType": "Buses",
        "buses": [],
    }
    for bus_id, bus_info in buses.items():
        bus_info = dataclasses.asdict(bus_info.get("busInfo"))
        if not window.is_inside(bus_info.get('lat'), bus_info.get('lng')):
            continue
        route = bus_info.get("route").split('-')[0]
        bus = {"busId": bus_id, "lat": bus_info.get('lat'), 
                "lng": bus_info.get("lng"), "route": route}
        message["buses"].append(bus)
    return message



async def listen_browser(ws):
    global window
    logger = logging.getLogger("bus")
    logger.info("listen to the browser")
    while True:
        message = await ws.get_message()
        window.update(json.loads(message).get("data"))
        print(dataclasses.asdict(window))
        logger.info('Received message: %s', message)


async def send_to_browser(ws):
    global buses
    while True:
        try:
            message = make_message_to_browser(buses)
            #print(len(message.get("buses")))
            await ws.send_message(json.dumps(message))
            await trio.sleep(.2)
        except ConnectionClosed:
            break


async def talk_to_browser(request):
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_to_browser, ws)
        nursery.start_soon(listen_browser, ws)


async def get_buses(request):
    global buses
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            message = json.loads(message)
            buses[message.get("busId")] = {"busInfo": Bus(message.get("lat"), 
                                                          message.get("lng"), 
                                                          message.get("route"))}
            #{"busInfo":{"lat":message.get("lat"),"lng": message.get("lng"), "route": message.get("route")}}
        except ConnectionClosed:
            break

def create_logger():
    # create logger
    logger = logging.getLogger('bus')
    logger.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)


async def main():
    create_logger()
    bus_reader = partial(serve_websocket, get_buses,
                         "127.0.0.1", 8080, ssl_context=None)
    bus_sender = partial(serve_websocket, talk_to_browser,
                         "127.0.0.1", 8000, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(bus_reader)
        nursery.start_soon(bus_sender)


if __name__ == "__main__":
    trio.run(main)
