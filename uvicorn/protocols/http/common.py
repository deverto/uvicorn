from abc import ABC, abstractmethod
from time import time


class BaseRequestResponseCycle(ABC):
    def __init__(self):
        self.on_response = ...
        self.scope = ...
        self.logger = ...
        self.response_started = ...
        self.transport = ...
        self.disconnected = ...
        self.response_complete = ...
        self._request_processing_start_time = ...

    @abstractmethod
    async def receive(self):
        ...

    @abstractmethod
    async def send_500_response(self):
        ...

    @abstractmethod
    async def send(self, *args, **kwargs):
        ...

    # ASGI exception wrapper
    async def run_asgi(self, app):
        try:
            self._request_processing_start_time = time()
            result = await app(self.scope, self.receive, self.send)
        except BaseException as exc:
            msg = "Exception in ASGI application\n"
            self.logger.error(msg, exc_info = exc)
            if not self.response_started:
                await self.send_500_response()
            else:
                self.transport.close()
        else:
            if result is not None:
                msg = "ASGI callable should return None, but returned '%s'."
                self.logger.error(msg, result)
                self.transport.close()
            elif not self.response_started and not self.disconnected:
                msg = "ASGI callable returned without starting response."
                self.logger.error(msg)
                await self.send_500_response()
            elif not self.response_complete and not self.disconnected:
                msg = "ASGI callable returned without completing response."
                self.logger.error(msg)
                self.transport.close()
        finally:
            self.on_response = None

    def _get_formatted_elapsed_ms(self):
        elapsed_ms = (time() - self._request_processing_start_time) * 1000
        return f"{elapsed_ms:.2f} ms"
