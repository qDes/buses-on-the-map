import trio
import json

from sys import stderr
from trio_websocket import open_websocket_url

import os


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


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


async def run_bus(url, bus_id, route):
    async with open_websocket_url(url) as ws:
        while True:
            for coordinate in route:
                message = make_message(bus_id, coordinate)
                await ws.send_message(json.dumps(message))
                await trio.sleep(1)


async def main():
    try:
        url = 'ws://127.0.0.1:8080'
        async with trio.open_nursery() as nursery:
            for route in load_routes():
                bus = route.get('name')
                coordinates = route.get('coordinates')
                nursery.start_soon(run_bus,url, bus, coordinates)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)


trio.run(main)
