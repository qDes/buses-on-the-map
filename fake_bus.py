import json
import logging
import os
import random
import trio
import time

import asyncclick as click
import trio_websocket
from sys import stderr
from trio_websocket import open_websocket_url
from itertools import islice
from functools import wraps

from trio_websocket._impl import HandshakeError, ConnectionClosed

def relaunch_on_disconnect(timeout):
    def actual_decorator(async_function):
        @wraps(async_function)
        async def with_reconnect(*args, **kwargs):
            while True:
                try:
                    await async_function(*args, **kwargs)
                except (ConnectionClosed, HandshakeError):
                    logging.info("Try to reconnect")
                    time.sleep(timeout)
        return with_reconnect
    return actual_decorator


def load_routes(directory_path):
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


def generate_bus_id(route_id, bus_index, emulator_id):
    return f"{route_id}-{bus_index}-{emulator_id}"


async def run_bus(send_chanel, bus_id, route):
    start_offset = random.randint(1, len(route))
    for coordinate in route[start_offset:]:
        message = make_message(bus_id, coordinate)
        await send_chanel.send(json.dumps(message, ensure_ascii=False))
        await trio.sleep(1)
    while True:
        for coordinate in route:
            message = make_message(bus_id, coordinate)
            await send_chanel.send(json.dumps(message, ensure_ascii=False))
            await trio.sleep(1)


@relaunch_on_disconnect(timeout=1)
async def send_updates(server_address, receive_channel):
    async with open_websocket_url(server_address) as ws:
        while True:
            message = await receive_channel.receive()
            await ws.send_message(message)


@click.command()
@click.option("-s", "--server", default="127.0.0.1:8080")
@click.option("-r", "--routes_number", default=50)
@click.option("-b", "--buses_per_route", default=5)
@click.option("-w", "--websockets_number", default=3)
@click.option("-e", "--emulator_id", default=0)
@click.option("-t", "--refresh_timeout", default=1)
@click.option("-v", default=False, help="enable logging")
async def main(server, routes_number, buses_per_route,
               websockets_number, emulator_id,
               refresh_timeout, v):
    if v:
        FORMAT = "%(levelname)s:root: %(message)s"
        logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    try:
        url = f"ws://{server}"
        async with trio.open_nursery() as nursery:
            # Open a channel:
            send_channels = []
            receive_channels = []
            for _ in range(websockets_number):
                send_channel, receive_channel = trio.open_memory_channel(0)
                send_channels.append(send_channel)
                receive_channels.append(receive_channel)
            for route in islice(load_routes("routes"), 0, routes_number):
                for bus_num in range(buses_per_route):
                    bus = generate_bus_id(route.get('name'),
                                          bus_num,
                                          emulator_id)
                    coordinates = route.get('coordinates')
                    nursery.start_soon(run_bus,
                                       random.choice(send_channels),
                                       bus,
                                       coordinates)
            for receive_channel in receive_channels:
                nursery.start_soon(send_updates, url, receive_channel)
    except OSError as ose:
        logging('Connection attempt failed: %s' % ose, file=stderr)


if __name__ == "__main__":
    main(_anyio_backend="trio")
