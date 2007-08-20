# Copyright (C) 2006-2007 Red Hat, Inc.
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
import os
import threading
import traceback
import xmlrpclib
import sys
import httplib
import urllib
import fcntl
import tempfile

import gobject
import SimpleXMLRPCServer
import SimpleHTTPServer
import SocketServer


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

    def close_request(self, request):
        """Called to clean up an individual request."""
        # let the request be closed by the request handler when its done
        pass


class ChunkedGlibHTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """RequestHandler class that integrates with Glib mainloop.  It writes
       the specified file to the client in chunks, returning control to the
       mainloop between chunks.
    """

    CHUNK_SIZE = 4096

    def __init__(self, request, client_address, server):
        self._file = None
        self._srcid = 0
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def log_request(self, code='-', size='-'):
        pass

    def do_GET(self):
        """Serve a GET request."""
        self._file = self.send_head()
        if self._file:
            self._srcid = gobject.io_add_watch(self.wfile, gobject.IO_OUT | gobject.IO_ERR, self._send_next_chunk)
        else:
            self._file.close()
            self._cleanup()

    def _send_next_chunk(self, source, condition):
        if condition & gobject.IO_ERR:
            self._cleanup()
            return False
        if not (condition & gobject.IO_OUT):
            self._cleanup()
            return False
        data = self._file.read(self.CHUNK_SIZE)
        count = os.write(self.wfile.fileno(), data)
        if count != len(data) or len(data) != self.CHUNK_SIZE:
            self._cleanup()
            return False
        return True

    def _cleanup(self):
        if self._file:
            self._file.close()
            self._file = None
        if self._srcid > 0:
            gobject.source_remove(self._srcid)
            self._srcid = 0
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()
        
    def finish(self):
        """Close the sockets when we're done, not before"""
        pass

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        ** [dcbw] modified to send Content-disposition filename too
        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.send_header("Content-Length", str(os.fstat(f.fileno())[6]))
        self.send_header("Content-Disposition", 'attachment; filename="%s"' % os.path.basename(path))
        self.end_headers()
        return f

class GlibURLDownloader(gobject.GObject):
    """Grabs a URL in chunks, returning to the mainloop after each chunk"""

    __gsignals__ = {
        'finished': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
        'error':    (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'progress': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT]))
    }

    CHUNK_SIZE = 4096

    def __init__(self, url, destdir=None):
        self._url = url
        if not destdir:
            destdir = tempfile.gettempdir()
        self._destdir = destdir
        self._srcid = 0
        self._fname = None
        self._outf = None
        self._written = 0
        gobject.GObject.__init__(self)

    def start(self, destfile=None, destfd=None):
        self._info = urllib.urlopen(self._url)
        self._outf = None
        self._fname = None
        if destfd and not destfile:
            raise ValueError("Must provide destination file too when specifying file descriptor")
        if destfile:
            self._suggested_fname = os.path.basename(destfile)
            self._fname = os.path.abspath(os.path.expanduser(destfile))
            if destfd:
                # Use the user-supplied destination file descriptor
                self._outf = destfd
            else:
                self._outf = os.open(self._fname, os.O_RDWR | os.O_TRUNC | os.O_CREAT, 0644)
        else:
            self._suggested_fname = self._get_filename_from_headers(self._info.headers)
            garbage, path = urllib.splittype(self._url)
            garbage, path = urllib.splithost(path or "")
            path, garbage = urllib.splitquery(path or "")
            path, garbage = urllib.splitattr(path or "")
            suffix = os.path.splitext(path)[1]
            (self._outf, self._fname) = tempfile.mkstemp(suffix=suffix, dir=self._destdir)

        fcntl.fcntl(self._info.fp.fileno(), fcntl.F_SETFD, os.O_NDELAY)
        self._srcid = gobject.io_add_watch(self._info.fp.fileno(),
                                           gobject.IO_IN | gobject.IO_ERR,
                                           self._read_next_chunk)

    def cancel(self):
        if self._srcid == 0:
            raise RuntimeError("Download already canceled or stopped")
        self.cleanup(remove=True)

    def _get_filename_from_headers(self, headers):
        if not headers.has_key("Content-Disposition"):
            return None

        ftag = "filename="
        data = headers["Content-Disposition"]
        fidx = data.find(ftag)
        if fidx < 0:
            return None
        fname = data[fidx+len(ftag):]
        if fname[0] == '"' or fname[0] == "'":
            fname = fname[1:]
        if fname[len(fname)-1] == '"' or fname[len(fname)-1] == "'":
            fname = fname[:len(fname)-1]
        return fname

    def _read_next_chunk(self, source, condition):
        if condition & gobject.IO_ERR:
            self.cleanup(remove=True)
            self.emit("error", "Error downloading file.")
            return False
        elif not (condition & gobject.IO_IN):
            # shouldn't get here, but...
            return True

        try:
            data = self._info.fp.read(self.CHUNK_SIZE)
            count = os.write(self._outf, data)
            self._written += len(data)

            # error writing data to file?
            if count < len(data):
                self.cleanup(remove=True)
                self.emit("error", "Error writing to download file.")
                return False

            self.emit("progress", self._written)

            # done?
            if len(data) < self.CHUNK_SIZE:
                self.cleanup()
                self.emit("finished", self._fname, self._suggested_fname)
                return False
        except Exception, err:
            self.cleanup(remove=True)
            self.emit("error", "Error downloading file: %s" % err)
            return False
        return True

    def cleanup(self, remove=False):
        if self._srcid > 0:
            gobject.source_remove(self._srcid)
            self._srcid = 0
        del self._info
        self._info = None
        os.close(self._outf)
        if remove:
            os.remove(self._fname)
        self._outf = None


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

class GlibXMLRPCTransport(xmlrpclib.Transport):
    """Integrate the request with the glib mainloop rather than blocking."""
    ##
    # Connect to server.
    #
    # @param host Target host.
    # @return A connection handle.

    def __init__(self, use_datetime=0):
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

    def start_request(self, host, handler, request_body, verbose=0, reply_handler=None, error_handler=None, user_data=None):
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
        gobject.io_add_watch(h._conn.sock, gobject.IO_IN, self._finish_request,
                h, host, handler, verbose, reply_handler, error_handler, user_data)

    def _finish_request(self, source, condition, h, host, handler, verbose, reply_handler=None, error_handler=None, user_data=None):
        """Parse and return response when the remote server actually returns it."""
        if not (condition & gobject.IO_IN):
            return True

        try:
            errcode, errmsg, headers = h.getreply()
        except socket.error, err:
            if err[0] != 104:
                raise socket.error(err)
            else:
                if error_handler:
                    gobject.idle_add(error_handler, err, user_data)
                return False
                
        if errcode != 200:
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)
        self.verbose = verbose        
        response = self._parse_response(h.getfile(), h._conn.sock)
        if reply_handler:
            # Coerce to a list so we can append user data
            response = response[0]
            if not isinstance(response, list):
                response = [response]
            response.append(user_data)
            gobject.idle_add(reply_handler, *response)
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
    def __call__(self, *args, **kwargs):
        return self.__send(self.__name, *args, **kwargs)


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

    def __request(self, methodname, *args, **kwargs):
        """Call the method on the remote server.  We just start the request here
        and the transport itself takes care of scheduling the response callback
        when the remote server returns the response.  We don't want to block anywhere."""

        request = xmlrpclib.dumps(args, methodname, encoding=self._encoding,
                        allow_none=self._allow_none)

        reply_hdl = kwargs.get("reply_handler")
        err_hdl = kwargs.get("error_handler")
        udata = kwargs.get("user_data")
        try:
            response = self._transport.start_request(
                self._host,
                self._handler,
                request,
                verbose=self._verbose,
                reply_handler=reply_hdl,
                error_handler=err_hdl,
                user_data=udata
                )
        except socket.error, exc:
            if err_hdl:
                gobject.idle_add(err_hdl, exc, udata)

    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self.__request, name)


class Test(object):
    def test(self, arg1, arg2):
        print "Request got %s, %s" % (arg1, arg2)
        return "success", "bork"

def xmlrpc_success_cb(response, resp2, loop):
    print "Response was %s %s" % (response, resp2)
    loop.quit()

def xmlrpc_error_cb(err, loop):
    print "Error: %s" % err
    loop.quit()

def xmlrpc_test(loop):
    client = GlibServerProxy("http://127.0.0.1:8888")
    client.test("bar", "baz",
                reply_handler=xmlrpc_success_cb,
                error_handler=xmlrpc_error_cb,
                user_data=loop)

def start_xmlrpc():
    server = GlibXMLRPCServer(("", 8888))
    inst = Test()
    server.register_instance(inst)
    gobject.idle_add(xmlrpc_test, loop)

class TestReqHandler(ChunkedGlibHTTPRequestHandler):
    def translate_path(self, path):
        return "/tmp/foo"

def start_http():
    server = GlibTCPServer(("", 8890), TestReqHandler)

def main():
    loop = gobject.MainLoop()
#    start_xmlrpc()
    start_http()
    try:
        loop.run()
    except KeyboardInterrupt:
        print 'Ctrl+C pressed, exiting...'
    print "Done."

if __name__ == "__main__":
    main()


