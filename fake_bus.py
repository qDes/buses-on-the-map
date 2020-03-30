import trio
import json
import os
import random

from sys import stderr
from trio_websocket import open_websocket_url



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


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


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
    '''   
    async with open_websocket_url(url) as ws:
        start_offset = random.randint(1, len(route))
        for coordinate in route[start_offset:]:
            message = make_message(bus_id, coordinate)
            await ws.send_message(json.dumps(message,
                                             ensure_ascii=False))
            await trio.sleep(1)
        while True:
            for coordinate in route:
                message = make_message(bus_id, coordinate)
                await ws.send_message(json.dumps(message,
                                                 ensure_ascii=False))
                await trio.sleep(1)
    '''


async def send_updates(server_address, receive_channel):
    async with open_websocket_url(server_address) as ws:
        while True:
            pass
            message = await receive_channel.receive()
            await ws.send_message(message)
'''
async def producer(send_channel):
    # Producer sends 3 messages
    for i in range(3):
        # The producer sends using 'await send_channel.send(...)'
        await send_channel.send("message {}".format(i))


async def consumer(receive_channel):
    # The consumer uses an 'async for' loop to receive the values:
    async for value in receive_channel:
        print("got value {!r}".format(value))
'''

async def main():
    try:
        url = 'ws://127.0.0.1:8080'
        async with trio.open_nursery() as nursery:
            # Open a channel:
            send_channel, receive_channel = trio.open_memory_channel(0)
            # Start a producer and a consumer, passing one end of the channel to
            # each of them:
            # nursery.start_soon(producer, send_channel)
            # nursery.start_soon(consumer, receive_channel)
            
            for route in load_routes():
                for i in range(15):
                    bus = generate_bus_id(route.get('name'), i)
                    coordinates = route.get('coordinates')
                    nursery.start_soon(run_bus, send_channel, bus, coordinates)
            nursery.start_soon(send_updates, url, receive_channel)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)


trio.run(main)
