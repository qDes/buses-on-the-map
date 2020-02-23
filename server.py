import json
import trio

from trio_websocket import serve_websocket, ConnectionClosed


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


async def echo_server(request):
    ws = await request.accept()
    route, coordinates = get_bus_from_file('156.json')

    while True:
        try:
            for coordinate in coordinates:
                message = make_message(route, coordinate)
                await trio.sleep(1)
                await ws.send_message(json.dumps(message))
        except ConnectionClosed:
            break


async def server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            print(message)
            #await ws.send_message(message)
        except ConnectionClosed:
            break

async def main():
    #await serve_websocket(echo_server, "127.0.0.1", 8000, ssl_context=None)
    await serve_websocket(server, "127.0.0.1", 8080, ssl_context=None)

if __name__ == "__main__":
    trio.run(main)
