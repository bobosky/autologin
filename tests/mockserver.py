#!/usr/bin/env python
import sys, time
from subprocess import Popen, PIPE

from scrapy.utils.log import configure_logging
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.util import Redirect
from twisted.web.server import Site


configure_logging()


class MockServer():
    def __init__(self):
        self.proc = None

    def __enter__(self):
        self.proc = Popen(
            [sys.executable, '-u', '-m', 'tests.mockserver'], stdout=PIPE)
        self.proc.stdout.readline()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.proc.kill()
        self.proc.wait()
        time.sleep(0.2)


PORT = 8781

AUTH_FORM = (
    '<form action="{action}" method="POST">'
    '<input type="text" name="login">'
    '<input type="password" name="password">'
    '<input type="submit" value="Login">'
    '</form>'
    )

class Login(Resource):
    isLeaf = True

    def render_GET(self, request):
        request.setHeader(b'utm', b'mark')
        if b'hide' in request.args:
            return b'<h1>Empty</h1>'
        auth = request.received_cookies.get(b'_auth') == b'yes'
        return (
            '<h1>Auth: {auth}</h1>' + AUTH_FORM
            ).format(action='login1', auth=auth).encode('utf-8')

    def render_POST(self, request):
        if (request.args[b'login'][0] == b'admin' and
                request.args[b'password'][0] == b'secret'):
            request.setHeader(b'set-cookie', b'_auth=yes')
        elif request.received_cookies.get(b'_auth'):
            request.setHeader(b'set-cookie', b'_auth=')
        return Redirect(b'/login1').render(request)


class LoginNoChangeCookie(Resource):
    isLeaf = True

    def render_GET(self, request):
        request.setHeader(b'set-cookie', b'session=1')
        if not hasattr(self, 'is_auth'):
            self.is_auth = False
        if self.is_auth:
            return b'You have logged in'
        else:
            return AUTH_FORM.format(action='login2').encode('utf-8')

    def render_POST(self, request):
        self.is_auth = (
            request.args[b'login'][0] == b'admin' and
            request.args[b'password'][0] == b'secret')
        return Redirect(b'/login2').render(request)


class Root(Resource):
    def __init__(self):
        Resource.__init__(self)
        self.putChild(b'login1', Login())
        self.putChild(b'login2', LoginNoChangeCookie())


def main():
    http_port = reactor.listenTCP(PORT, Site(Root()))
    def print_listening():
        host = http_port.getHost()
        print('Mock server running at http://{}:{}'.format(
            host.host, host.port))
    reactor.callWhenRunning(print_listening)
    reactor.run()


if __name__ == "__main__":
    main()