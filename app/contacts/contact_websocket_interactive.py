import asyncio
import time
import websockets
import json
from app.utility.base_world import BaseWorld


class Contact(BaseWorld):

    def __init__(self, services):
        self.name = 'websocket'
        self.description = 'Accept data through web sockets'
        self.log = self.create_logger('contact_websocket_interactive')
        self.handler = Handler(services)
        self.stop_future = asyncio.Future()

    async def start(self):
        web_socket = self.get_config('app.contact.websocket_interactive') # Does not appear to pull form default conf well.
        web_socket = "0.0.0.0:7013" 
        self.log.info("Starting websocket on %s" % web_socket)
        try:
            async with websockets.serve(self.handler.handle, web_socket.split(':')[0], web_socket.split(':')[1]):
                # as soon as we start serving from websockets, we need to suppress their excessive debug messages
                self.log.manager.loggerDict['websockets.protocol'].level = 100
                self.log.manager.loggerDict['websockets.server'].level = 100

                await self.stop_future

        except OSError as e:
            self.log.error("WebSocket error: {}".format(e))

    async def stop(self):
        self.stop_future.set_result('')


class Handler:
    def __init__(self, services):
        self.services = services
        self.handles = []
        self.name = "Websocket"
        self.contact_svc = services.get('contact_svc')
        self.log = BaseWorld.create_logger('websocket_handler')
        self.log.info("Handle init")

    async def handle(self, socket, path):
        self.log.info("Handle handle")
        # try:
        while True:
            message = await socket.recv()
            print(message)
            profile = json.loads(self.contact_svc.decode_bytes(message))
            print(profile)
            profile['paw'] = profile.get('paw')
            print(profile['paw'])
            profile['contact'] = profile.get('contact', self.name)
            print(profile['contact'])
            while True:
                print("Getting instructions")
                agent, instructions = await self.contact_svc.handle_heartbeat(**profile)
                inst_tmp = json.dumps([json.dumps(i.display) for i in instructions])
                break
                # The server gets stuck in this loop and the rest of caldera freezes.
                # if len(instructions) > 0:
                #     break
                # else:
                #     time.sleep(1)
            response = dict(paw=agent.paw,
                            sleep=await agent.calculate_sleep(),
                            watchdog=agent.watchdog,
                            instructions=inst_tmp)
            if agent.pending_contact != agent.contact:
                response['new_contact'] = agent.pending_contact
                self.log.debug('Sending agent instructions to switch from C2 channel %s to %s' % (agent.contact, agent.pending_contact))
            if agent.executor_change_to_assign:
                response['executor_change'] = agent.assign_pending_executor_change()
                self.log.debug('Asking agent to update executor: %s', response.get('executor_change'))
            response['sleep'] = 2 # We want sleep 0 but that will spam request and response so fast the whole server stops.
            print(response)
            await socket.send(self.contact_svc.encode_string(json.dumps(response)))

        # except Exception as e:
        #     self.log.debug(e)