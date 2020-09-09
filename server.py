import json
import logging
import trio

from functools import partial
from trio_websocket import serve_websocket, ConnectionClosed

buses = dict()
window = dict()

def get_bus_from_file(filename):
    with open(filename, 'r') as f:
        bus = json.loads(f.read())
    bus_name = bus.get('name')
    bus_coordinates = bus.get('coordinates')
    return bus_name, bus_coordinates


def make_message(route, coordinate):
    message = {
        "msgType": "Buses",
        "buses": [
            {"busId": "c790сс", "lat": coordinate[0], 
             "lng": coordinate[1], "route": route},
        ],
    }
    return message


def make_message_to_browser(buses):
    global window
    message = {
        "msgType": "Buses",
        "buses": [],
    }
    for bus_id, bus_info in buses.items():
        bus_info = bus_info.get("busInfo")
        if not is_inside(window, bus_info.get('lat'), bus_info.get('lng')):
            continue
        route = bus_info.get("route").split('-')[0]
        bus = {"busId": bus_id, "lat": bus_info.get('lat'), 
                "lng": bus_info.get("lng"), "route": route}
        message["buses"].append(bus)
    return message


def is_inside(bounds, lat, lng):
    if not bounds:
        return False
    if lat > bounds.get("north_lat"):
        return False
    if lat < bounds.get("south_lat"):
        return False
    if lng > bounds.get("east_lng"):
        return False
    if lng < bounds.get("west_lng"):
        return False
    return True


async def listen_browser(ws):
    global window
    logger = logging.getLogger("bus")
    logger.info("listen to the browser")
    while True:
        message = await ws.get_message()
        window = json.loads(message).get("data")
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
    #global buses
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
            buses[message.get("busId")] = {"busInfo":{"lat":message.get("lat"),
        "lng": message.get("lng"), "route": message.get("route")}}
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
