import json
import trio

from functools import partial
from trio_websocket import serve_websocket, ConnectionClosed

buses = dict()


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
    message = {
        "msgType": "Buses",
        "buses": [],
    }
    for bus_id, bus_info in buses.items():
        bus_info = bus_info.get("busInfo")
        route = bus_info.get("route").split('-')[0]
        bus = {"busId": bus_id, "lat": bus_info.get('lat'), 
                "lng": bus_info.get("lng"), "route": route}
        message["buses"].append(bus)
    return message
 

async def listen_browser(ws):
    while True:
        message = await ws.get_message()
        print('Received message: %s', message)


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



async def main():
    bus_reader = partial(serve_websocket, get_buses,
                         "127.0.0.1", 8080, ssl_context=None)
    bus_sender = partial(serve_websocket, talk_to_browser,
                         "127.0.0.1", 8000, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(bus_reader)
        nursery.start_soon(bus_sender)


if __name__ == "__main__":
    trio.run(main)
