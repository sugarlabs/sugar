import dbus

_installed = False
fake_get_object = None

def _install():
    global _installed, fake_get_object
    if _installed:
        return
    bus = dbus.SessionBus()
    old_get_object = bus.get_object
    fake_get_object = FakeGetObject(old_get_object)
    bus.get_object = fake_get_object
    _installed = True
    # @@: Do we need to override bus.add_signal_receiver?

class FakeGetObject(object):

    def __init__(self, real_get_object):
        self._real_get_object = real_get_object
        self._overrides = {}

    def register(self, service, service_name, path):
        self._overrides[(service_name, path)] = service

    def __call__(self, service_name, path):
        override = self._overrides.get((service_name, path), None)
        if override is None:
            return self._real_get_object(service_name, path)
        else:
            return override

class MockService(object):

    def __init__(self, service_name, path, name=None):
        self.service_name = service_name
        self.path = path
        if name is None:
            name = self.service_name
        self.name = name
        self._connections = {}
        self._pending_responses = {}
        self._pending_requests = {}

    def __repr__(self):
        if self.name == self.service_name:
            return '<%s %s:%s>' % (
                self.__class__.__name__,
                self.service_name, self.path)
        else:
            return '<%s %s %s:%s>' % (
                self.__class__.__name__,
                self.name,
                self.service_name, self.path)

    def install(self):
        _install()
        fake_get_object.register(
            self, self.service_name, self.path)

    def __getattr__(self, attr, dbus_interface=None):
        if attr == 'make_response':
            return BoundInterface(self.make_response, dbus_interface)
        return MockMethod(self, attr, dbus_interface)

    def call(self, meth_name, dbus_interface, *args, **kw):
        formatted = [repr(a) for a in args]
        formatted.extend(['%s=%r' % item for item in kw.items()])
        formatted = ', '.join(formatted)
        print 'Called %s.%s:%s(%s)' % (self.name, dbus_interface, meth_name, formatted)
        if 'reply_handler' in kw:
            reply_handler = kw.pop('reply_handler')
        else:
            reply_handler = None
        if 'error_handler' in kw:
            error_handler = kw.pop('error_handler')
        else:
            error_handler = None
        key = (meth_name, dbus_interface)
        if reply_handler:
            if key in self._pending_requests:
                raise ValueError(
                    "Duplicate requests not yet handled for %s:%s" % (dbus_interface, meth_name))
            self._pending_requests[key] = (reply_handler, error_handler)
            self.call_responses()
            return
        assert error_handler is None, (
            "error_handler %s without reply_handler" % error_handler)
        if key not in self._pending_responses:
            if self._pending_responses:
                extra = '(have responses %s)' % self._response_description()
            else:
                extra = '(have no waiting responses)'
            raise ValueError(
                "You must call make_response() before %s:%s method "
                "is called %s"
                % (dbus_interface, meth_name, extra))
        error, response = self._pending_responses.pop(key)
        if error:
            # XXX: Is this how it should be raised?
            raise response
        else:
            return response

    def make_response(self, meth_name, response, error=False, dbus_interface=None):
        key = (meth_name, dbus_interface)
        if key in self._pending_responses:
            raise ValueError(
                "A response %r is already registered for %s:%s"
                % (self._pending_responses[key], dbus_interface, meth_name))
        self._pending_responses[key] = (error, response)

    def _response_description(self):
        result = []
        for meth_name, dbus_interface in sorted(self._pending_responses.keys()):
            value = self._pending_responses[(meth_name, dbus_interface)]
            result.append('%s:%s()=%r' % (dbus_interface, meth_name, value))
        return ', '.join(result)

    def call_responses(self):
        for key in sorted(self._pending_responses.keys()):
            if key in self._pending_requests:
                error, response = self._pending_responses[key]
                reply_handler, error_handler = self._pending_requests[key]
                if error:
                    # XXX: Is this how it should be raised?
                    error_handler(response)
                else:
                    reply_handler(response)
                del self._pending_responses[key]
                del self._pending_requests[key]

    def connect_to_signal(self, signal, handler_function,
                          dbus_interface=None, **kw):
        self._connections.setdefault((signal, dbus_interface), []).append(
            handler_function)

    def send_signal(self, signal, dbus_interface=None):
        for listener in self._connections.get((signal, dbus_interface), []):
            # @@: Argument?
            listener()

    @property
    def empty(self):
        return (
            not self._pending_responses
            and not self._pending_requests)

class MockMethod(object):

    def __init__(self, obj, meth_name, dbus_interface):
        self.obj = obj
        self.meth_name = meth_name
        self.dbus_interface = dbus_interface

    def __repr__(self):
        return '<%s.%s:%s method>' % (
            self.obj.name, self.meth_name, self.dbus_interface)

    def __call__(self, *args, **kw):
        return self.obj.call(
            self.meth_name, self.dbus_interface,
            *args, **kw)

class BoundInterface(object):

    def __init__(self, method, dbus_interface):
        self.method = method
        self.dbus_interface = dbus_interface

    def __repr__(self):
        return '<bound interface %s for %s>' % (
            self.dbus_interface, self.method)

    def __call__(self, *args, **kw):
        kw.setdefault('dbus_interface', self.dbus_interface)
        return self.method(*args, **kw)
        
