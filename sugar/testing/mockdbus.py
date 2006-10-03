"""
Module to mock out portions of the dbus library for testing purposes.

This is intended to be used with doctest, something like::
    
    >>> from sugar.testing import mockdbus
    >>> mock_service = mockdbus.MockService(
    ...     'service.name', '/service/path', name='printed_name')

This doesn't actually change anything, yes; you must install the mock
service to get it to run.  This actually modifies the dbus module in
place, and should only be used in a process dedicated to testing (you
shouldn't use this in normal code).  Next we install the service and
get the interface::
    
    >>> mock_service.install()
    >>> import dbus
    >>> mock_interface = dbus.Interface(mock_service, 'interface.name')

Before you trigger code that uses this mock service, you have to tell
the service how to respond, like::

    >>> mock_interface.make_response('methodName', 'response')

Next time mock_interface.methodName(any arguments) is called, it will
return 'response'.  Also, when that method is called it will print
out the call plus the arguments.  This works well with doctest, like::

    >>> mock_interface.methodName(1, 2)
    Called printed_name.interface.name:methodName(1, 2)
    'response'

(Note: the first line is printed, the second line is the return value)

It is an error if a method is called that has no response setup,
unless that method is called asynchronously (with reply_handler).
Then the reply_handler will be called as soon as the response has been
created with service.make_response().  By delaying the response you
can force response handlers to run out of order.

"""

import dbus

_installed = False
fake_get_object = None

def _install():
    """
    Installs the monkeypatch to dbus.  Called automatically when
    necessary.
    """
    global _installed, fake_get_object
    if _installed:
        return
    bus = dbus.SessionBus()
    old_get_object = bus.get_object
    fake_get_object = FakeGetObject(old_get_object)
    bus.get_object = fake_get_object
    _installed = True
    # XXX: Do we need to override bus.add_signal_receiver?

class FakeGetObject(object):

    """
    The replacement dbus.get_object() function/callable.  This
    delegates to the real get_object callable, except when a
    MockService has been registered.
    """

    def __init__(self, real_get_object):
        self._real_get_object = real_get_object
        self._overrides = {}

    def register(self, mock_service, service_name, path):
        """
        Registers a MockService instance to the service_name and path.
        Calls to dbus.get_object(service_name, path) will now return
        this mock_service object.
        """
        self._overrides[(service_name, path)] = mock_service

    def __call__(self, service_name, path):
        override = self._overrides.get((service_name, path), None)
        if override is None:
            return self._real_get_object(service_name, path)
        else:
            return override

class MockService(object):

    """
    A mock service object.  You should first instantiate then install
    this object.  Once installed, calls to
    dbus.get_object(service_name, path) will return this object
    instead of a real dbus service object.
    """

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
        """
        Installs this object.
        """
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
            self.call_reply_handlers()
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

    def make_response(self, meth_name, response, error=False,
                      dbus_interface=None):
        """
        This is used to generate a response to a method call.  If
        error is true, then the response object is an exception that
        will be raised (or passed to error_handler).
        """
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

    def call_reply_handlers(self):
        """
        This calls any reply_handlers that now have responses (or
        errors) ready for them.  This can be called when a response is
        added after an asynchronous method is called, to trigger the
        response actually being called.
        """
        # XXX: Should make_response automatically call this?
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
        # XXX: This isn't really done
        for listener in self._connections.get((signal, dbus_interface), []):
            # XXX: Argument?
            listener()

    @property
    def empty(self):
        """
        This can be called to at the end of the test to make sure
        there's no responses or requests left over.
        """
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
        
