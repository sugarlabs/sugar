# Copyright (C) 2006, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

# pylint: disable-msg = W0221

import socket
import threading
import traceback
import xmlrpclib
import sys
import httplib

import gobject
import SimpleXMLRPCServer
import SocketServer


RESULT_FAILED = 0
RESULT_SUCCESS = 1

__authinfos = {}

def _add_authinfo(authinfo):
    __authinfos[threading.currentThread()] = authinfo

def get_authinfo():
    return __authinfos.get(threading.currentThread())

def _del_authinfo():
    del __authinfos[threading.currentThread()]


class GlibTCPServer(SocketServer.TCPServer):
    """GlibTCPServer

    Integrate socket accept into glib mainloop.
    """

    allow_reuse_address = True
    request_queue_size = 20

    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
        self.socket.setblocking(0)  # Set nonblocking

        # Watch the listener socket for data
        gobject.io_add_watch(self.socket, gobject.IO_IN, self._handle_accept)

    def _handle_accept(self, source, condition):
        """Process incoming data on the server's socket by doing an accept()
        via handle_request()."""
        if not (condition & gobject.IO_IN):
            return True
        self.handle_request()
        return True

class GlibXMLRPCRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    """ GlibXMLRPCRequestHandler
    
    The stock SimpleXMLRPCRequestHandler and server don't allow any way to pass
    the client's address and/or SSL certificate into the function that actually
    _processes_ the request.  So we have to store it in a thread-indexed dict.
    """

    def do_POST(self):
        _add_authinfo(self.client_address)
        try:
            SimpleXMLRPCServer.SimpleXMLRPCRequestHandler.do_POST(self)
        except socket.timeout:
            pass
        except socket.error, e:
            print "Error (%s): socket error - '%s'" % (self.client_address, e)
        except:
            print "Error while processing POST:"
            traceback.print_exc()
        _del_authinfo()

class GlibXMLRPCServer(GlibTCPServer, SimpleXMLRPCServer.SimpleXMLRPCDispatcher):
    """GlibXMLRPCServer
    
    Use nonblocking sockets and handle the accept via glib rather than
    blocking on accept().
    """

    def __init__(self, addr, requestHandler=GlibXMLRPCRequestHandler,
                 logRequests=0, allow_none=False):
        self.logRequests = logRequests
        if sys.version_info[:3] >= (2, 5, 0):
            SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self, allow_none, encoding="utf-8")
        else:
            SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self)
        GlibTCPServer.__init__(self, addr, requestHandler)

    def _marshaled_dispatch(self, data, dispatch_method = None):
        """Dispatches an XML-RPC method from marshalled (XML) data.

        XML-RPC methods are dispatched from the marshalled (XML) data
        using the _dispatch method and the result is returned as
        marshalled data. For backwards compatibility, a dispatch
        function can be provided as an argument (see comment in
        SimpleXMLRPCRequestHandler.do_POST) but overriding the
        existing method through subclassing is the prefered means
        of changing method dispatch behavior.
        """

        params, method = xmlrpclib.loads(data)

        # generate response
        try:
            if dispatch_method is not None:
                response = dispatch_method(method, params)
            else:
                response = self._dispatch(method, params)
            # wrap response in a singleton tuple
            response = (response,)
            response = xmlrpclib.dumps(response, methodresponse=1)
        except xmlrpclib.Fault, fault:
            response = xmlrpclib.dumps(fault)
        except:
            print "Exception while processing request:"
            traceback.print_exc()

            # report exception back to server
            response = xmlrpclib.dumps(
                xmlrpclib.Fault(1, "%s:%s" % (sys.exc_type, sys.exc_value))
                )

        return response


class GlibHTTP(httplib.HTTP):
    """Subclass HTTP so we can return it's connection class' socket."""
    def connect(self, host=None, port=None):
        httplib.HTTP.connect(self, host, port)
        self._conn.sock.setblocking(0)
    def get_sock(self):
        return self._conn.sock

class GlibXMLRPCTransport(xmlrpclib.Transport):
    """Integrate the request with the glib mainloop rather than blocking."""
    ##
    # Connect to server.
    #
    # @param host Target host.
    # @return A connection handle.

    def __init__(self):
        if sys.version_info[:3] >= (2, 5, 0):
            xmlrpclib.Transport.__init__(self, use_datetime)

    def make_connection(self, host):
        """Use our own connection object so we can get its socket."""
        # create a HTTP connection object from a host descriptor
        host, extra_headers, x509 = self.get_host_info(host)
        return GlibHTTP(host)

    ##
    # Send a complete request, and parse the response.
    #
    # @param host Target host.
    # @param handler Target PRC handler.
    # @param request_body XML-RPC request body.
    # @param verbose Debugging flag.
    # @return Parsed response.

    def start_request(self, host, handler, request_body, verbose=0, request_cb=None, user_data=None):
        """Do the first half of the request by sending data to the remote
        server.  The bottom half bits get run when the remote server's response
        actually comes back."""
        # issue XML-RPC request

        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        self.send_request(h, handler, request_body)
        self.send_host(h, host)
        self.send_user_agent(h)
        self.send_content(h, request_body)

        # Schedule a GIOWatch so we don't block waiting for the response
        gobject.io_add_watch(h.get_sock(), gobject.IO_IN, self._finish_request,
                h, host, handler, verbose, request_cb, user_data)

    def _finish_request(self, source, condition, h, host, handler, verbose, request_cb, user_data):
        """Parse and return response when the remote server actually returns it."""
        if not (condition & gobject.IO_IN):
            return True

        try:
            errcode, errmsg, headers = h.getreply()
        except socket.error, err:
            if err[0] != 104:
                raise socket.error(err)
            else:
                gobject.idle_add(request_cb, RESULT_FAILED, None, user_data)
                return False
                
        if errcode != 200:
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)
        self.verbose = verbose        
        response = self._parse_response(h.getfile(), h.get_sock())
        if request_cb:
            if len(response) == 1:
                response = response[0]
            gobject.idle_add(request_cb, RESULT_SUCCESS, response, user_data)
        return False

class _Method:
    """Right, so python people thought it would be funny to make this
    class private to xmlrpclib.py..."""
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
        self.__send = send
        self.__name = name
    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))
    def __call__(self, request_cb, user_data, *args):
        return self.__send(self.__name, request_cb, user_data, args)


class GlibServerProxy(xmlrpclib.ServerProxy):
    """Subclass xmlrpclib.ServerProxy so we can run the XML-RPC request
    in two parts, integrated with the glib mainloop, such that we don't
    block anywhere.
    
    Using this object is somewhat special; it requires more arguments to each
    XML-RPC request call than the normal xmlrpclib.ServerProxy object:
    
    client = GlibServerProxy("http://127.0.0.1:8888")
    user_data = "bar"
    xmlrpc_arg1 = "test"
    xmlrpc_arg2 = "foo"
    client.test(xmlrpc_test_cb, user_data, xmlrpc_arg1, xmlrpc_arg2)

    Here, 'xmlrpc_test_cb' is the callback function, which has the following
    signature:
    
    def xmlrpc_test_cb(result_status, response, user_data=None):
        ...
    """
    def __init__(self, uri, encoding=None, verbose=0, allow_none=0):
        self._transport = GlibXMLRPCTransport()
        self._encoding = encoding
        self._verbose = verbose
        self._allow_none = allow_none
        xmlrpclib.ServerProxy.__init__(self, uri, self._transport, encoding, verbose, allow_none)

        # get the url
        import urllib
        urltype, uri = urllib.splittype(uri)
        if urltype not in ("http", "https"):
            raise IOError, "unsupported XML-RPC protocol"
        self._host, self._handler = urllib.splithost(uri)
        if not self._handler:
            self._handler = "/RPC2"

    def __request(self, methodname, request_cb, user_data, params):
        """Call the method on the remote server.  We just start the request here
        and the transport itself takes care of scheduling the response callback
        when the remote server returns the response.  We don't want to block anywhere."""

        request = xmlrpclib.dumps(params, methodname, encoding=self._encoding,
                        allow_none=self._allow_none)

        try:
            response = self._transport.start_request(
                self._host,
                self._handler,
                request,
                verbose=self._verbose,
                request_cb=request_cb,
                user_data=user_data
                )
        except socket.error, exc:
            gobject.idle_add(request_cb, RESULT_FAILED, None, user_data)

    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self.__request, name)


class GroupServer(object):

    _MAX_MSG_SIZE = 500

    def __init__(self, address, port, data_cb):
        self._address = address
        self._port = port
        self._data_cb = data_cb

        self._setup_listener()

    def _setup_listener(self):
        # Listener socket
        self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set some options to make it multicast-friendly
        self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
        self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)

    def start(self):
        # Set some more multicast options
        self._listen_sock.bind(('', self._port))
        self._listen_sock.settimeout(2)
        intf = socket.gethostbyname(socket.gethostname())
        self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(intf) + socket.inet_aton('0.0.0.0'))
        self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self._address) + socket.inet_aton('0.0.0.0'))

        # Watch the listener socket for data
        gobject.io_add_watch(self._listen_sock, gobject.IO_IN, self._handle_incoming_data)

    def _handle_incoming_data(self, source, condition):
        if not (condition & gobject.IO_IN):
            return True
        msg = {}
        msg['data'], (msg['addr'], msg['port']) = source.recvfrom(self._MAX_MSG_SIZE)
        if self._data_cb:
            self._data_cb(msg)
        return True

class GroupClient(object):

    _MAX_MSG_SIZE = 500

    def __init__(self, address, port):
        self._address = address
        self._port = port

        self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Make the socket multicast-aware, and set TTL.
        self._send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20) # Change TTL (=20) to suit

    def send_msg(self, data):
        self._send_sock.sendto(data, (self._address, self._port))



class Test(object):
    def test(self, arg1):
        print "Request got %s" % arg1
        return "success"

def xmlrpc_test_cb(response, user_data=None):
    print "Response was %s, user_data was %s" % (response, user_data)
    import gtk
    gtk.main_quit()


def xmlrpc_test():
    client = GlibServerProxy("http://127.0.0.1:8888")
    client.test(xmlrpc_test_cb, "bar", "test data")


def main():
    import gtk
    server = GlibXMLRPCServer(("", 8888))
    inst = Test()
    server.register_instance(inst)
    
    gobject.idle_add(xmlrpc_test)

    try:
        gtk.main()
    except KeyboardInterrupt:
        print 'Ctrl+C pressed, exiting...'
    print "Done."

if __name__ == "__main__":
    main()
