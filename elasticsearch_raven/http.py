try:
    import queue
except ImportError:
    import Queue as queue

from elasticsearch_raven import configuration
from elasticsearch_raven.transport import LogTransport
from elasticsearch_raven.transport import SentryMessage
from elasticsearch_raven.udp_server import get_sender


class HttpUtils:
    def __init__(self):
        self._pending_logs = queue.Queue(configuration['queue_maxsize'])
        self._exception_queue = queue.Queue()

    def start_sender(self):
        transport = LogTransport(configuration['host'],
                                           configuration['use_ssl'])
        sender = get_sender(transport, self._pending_logs, self._exception_queue)
        sender.start()

    def get_application(self):
        def application(environ, start_response):
            try:
                exception = self._exception_queue.get_nowait()
            except queue.Empty:
                pass
            else:
                raise exception
            length = int(environ.get('CONTENT_LENGTH', '0'))
            data = environ['wsgi.input'].read(length)
            self._pending_logs.put(SentryMessage.create_from_http(
                environ['HTTP_X_SENTRY_AUTH'], data))

            status = '200 OK'
            response_headers = [('Content-Type', 'text/plain')]
            start_response(status, response_headers)
            return [''.encode('utf-8')]
        return application
