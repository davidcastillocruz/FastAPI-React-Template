from contextvars import ContextVar

# Values of the request being handled, readable from any function without passing them around:
# the logger adds them to every log line. Each request runs in its own asyncio task,
# with its own copy of these values, so requests at the same time never mix them
request_id: ContextVar[str] = ContextVar("request_id", default="-")
client_ip: ContextVar[str] = ContextVar("client_ip", default="-")
