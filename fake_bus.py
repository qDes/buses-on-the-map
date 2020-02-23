import trio
import json

from sys import stderr
from trio_websocket import open_websocket_url


def get_bus_from_file(filename):
    with open(filename, 'r') as f:
        bus = json.loads(f.read())
    bus_name = bus.get('name')
    bus_coordinates = bus.get('coordinates')
    return bus_name, bus_coordinates


def make_message(route, coordinate):
    message = {"busId": f"{route}-0", "lat": coordinate[0],
             "lng": coordinate[1], "route": route}
    return message


async def main():
    bus, coordinates = get_bus_from_file("156.json")
    try:
        async with open_websocket_url('ws://127.0.0.1:8080') as ws:
            while True:
                for coordinate in coordinates:
                    message = make_message(bus, coordinate)
                    await ws.send_message(json.dumps(message))
                    await trio.sleep(1)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)


trio.run(main)
