##############################################################################
#
# Copyright (c) 2009 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
import unittest

from ZPublisher.Publish import get_module_info


class WSGIResponseTests(unittest.TestCase):

    _old_NOW = None

    def tearDown(self):
        if self._old_NOW is not None:
            self._setNOW(self._old_NOW)

    def _getTargetClass(self):
        from ZPublisher.WSGIPublisher import WSGIResponse
        return WSGIResponse

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def _setNOW(self, value):
        from ZPublisher import WSGIPublisher
        WSGIPublisher._NOW, self._old_NOW = value, WSGIPublisher._NOW

    def test_finalize_sets_204_on_empty_not_streaming(self):
        response = self._makeOne()
        response.finalize()
        self.assertEqual(response.status, 204)

    def test_finalize_sets_204_on_empty_not_streaming_ignores_non_200(self):
        response = self._makeOne()
        response.setStatus(302)
        response.finalize()
        self.assertEqual(response.status, 302)

    def test_finalize_sets_content_length_if_missing(self):
        response = self._makeOne()
        response.setBody('TESTING')
        response.finalize()
        self.assertEqual(response.getHeader('Content-Length'), '7')

    def test_finalize_skips_content_length_if_missing_w_streaming(self):
        response = self._makeOne()
        response._streaming = True
        response.body = 'TESTING'
        response.finalize()
        self.assertFalse(response.getHeader('Content-Length'))

    def test_listHeaders_skips_Server_header_wo_server_version_set(self):
        response = self._makeOne()
        response.setBody('TESTING')
        headers = response.listHeaders()
        sv = [x for x in headers if x[0] == 'Server']
        self.assertFalse(sv)

    def test_listHeaders_includes_Server_header_w_server_version_set(self):
        response = self._makeOne()
        response._server_version = 'TESTME'
        response.setBody('TESTING')
        headers = response.listHeaders()
        sv = [x for x in headers if x[0] == 'Server']
        self.assertTrue(('Server', 'TESTME') in sv)

    def test_listHeaders_includes_Date_header(self):
        import time
        WHEN = time.localtime()
        self._setNOW(time.mktime(WHEN))
        response = self._makeOne()
        response.setBody('TESTING')
        headers = response.listHeaders()
        whenstr = time.strftime('%a, %d %b %Y %H:%M:%S GMT',
                                time.gmtime(time.mktime(WHEN)))
        self.assertTrue(('Date', whenstr) in headers)

    def test_setBody_IUnboundStreamIterator(self):
        from ZPublisher.Iterators import IUnboundStreamIterator
        from zope.interface import implements

        class TestStreamIterator(object):
            implements(IUnboundStreamIterator)
            data = "hello"
            done = 0

            def next(self):
                if not self.done:
                    self.done = 1
                    return self.data
                raise StopIteration

        response = self._makeOne()
        response.setStatus(200)
        body = TestStreamIterator()
        response.setBody(body)
        response.finalize()
        self.assertTrue(body is response.body)
        self.assertEqual(response._streaming, 1)

    def test_setBody_IStreamIterator(self):
        from ZPublisher.Iterators import IStreamIterator
        from zope.interface import implements

        class TestStreamIterator(object):
            implements(IStreamIterator)
            data = "hello"
            done = 0

            def next(self):
                if not self.done:
                    self.done = 1
                    return self.data
                raise StopIteration

            def __len__(self):
                return len(self.data)

        response = self._makeOne()
        response.setStatus(200)
        body = TestStreamIterator()
        response.setBody(body)
        response.finalize()
        self.assertTrue(body is response.body)
        self.assertEqual(response._streaming, 0)
        self.assertEqual(response.getHeader('Content-Length'),
                         '%d' % len(TestStreamIterator.data))

    def test___str___raises(self):
        response = self._makeOne()
        response.setBody('TESTING')
        self.assertRaises(NotImplementedError, lambda: str(response))


class TestPublish(unittest.TestCase):

    def _callFUT(self, request, module_info=None):
        from ZPublisher.WSGIPublisher import publish
        if module_info is None:
            module_info = get_module_info()

        return publish(request, module_info)

    def test_wo_REMOTE_USER(self):
        request = DummyRequest(PATH_INFO='/')
        response = request.response = DummyResponse()
        _before = DummyCallable()
        _after = object()
        _object = DummyCallable()
        _object._result = 'RESULT'
        request._traverse_to = _object
        _realm = 'TESTING'
        _debug_mode = True
        _err_hook = DummyCallable()
        _validated_hook = object()
        _tm = DummyTM()
        module_info = (_before, _after, _object, _realm, _debug_mode,
                       _err_hook, _validated_hook, _tm)
        returned = self._callFUT(request, module_info)
        self.assertTrue(returned is response)
        self.assertTrue(request._processedInputs)
        self.assertEqual(response.after_list, (_after,))
        self.assertTrue(response.debug_mode)
        self.assertEqual(response.realm, 'TESTING')
        self.assertEqual(_before._called_with, ((), {}))
        self.assertEqual(request['PARENTS'], [_object])
        self.assertEqual(request._traversed, ('/', None, _validated_hook))
        self.assertEqual(_tm._recorded, (_object, request))
        self.assertTrue(_tm._begin)
        self.assertTrue(_tm._commit)
        self.assertEqual(_object._called_with, ((), {}))
        self.assertEqual(response._body, 'RESULT')
        self.assertEqual(_err_hook._called_with, None)

    def test_w_REMOTE_USER(self):
        request = DummyRequest(PATH_INFO='/', REMOTE_USER='phred')
        response = request.response = DummyResponse()
        _before = DummyCallable()
        _after = object()
        _object = DummyCallable()
        _object._result = 'RESULT'
        request._traverse_to = _object
        _realm = 'TESTING'
        _debug_mode = True
        _err_hook = DummyCallable()
        _validated_hook = object()
        _tm = DummyTM()
        module_info = (_before, _after, _object, _realm, _debug_mode,
                       _err_hook, _validated_hook, _tm)
        self._callFUT(request, module_info)
        self.assertEqual(response.realm, None)


class TestPublishModule(unittest.TestCase):

    def setUp(self):
        from zope.testing.cleanup import cleanUp
        cleanUp()

    def tearDown(self):
        from zope.testing.cleanup import cleanUp
        cleanUp()

    def _callFUT(self, environ, start_response,
                 _publish=None, _response_factory=None, _request_factory=None):
        from ZPublisher.WSGIPublisher import publish_module
        if _publish is not None:
            if _response_factory is not None:
                if _request_factory is not None:
                    return publish_module(environ, start_response, _publish,
                                          _response_factory, _request_factory)
                return publish_module(environ, start_response, _publish,
                                      _response_factory)
            else:
                if _request_factory is not None:
                    return publish_module(environ, start_response, _publish,
                                          _request_factory=_request_factory)
                return publish_module(environ, start_response, _publish)
        return publish_module(environ, start_response)

    def _registerView(self, factory, name, provides=None):
        from zope.component import provideAdapter
        from zope.interface import Interface
        from zope.publisher.browser import IDefaultBrowserLayer
        from OFS.interfaces import IApplication
        if provides is None:
            provides = Interface
        requires = (IApplication, IDefaultBrowserLayer)
        provideAdapter(factory, requires, provides, name)

    def _makeEnviron(self, **kw):
        from StringIO import StringIO
        environ = {
            'SCRIPT_NAME': '',
            'REQUEST_METHOD': 'GET',
            'QUERY_STRING': '',
            'SERVER_NAME': '127.0.0.1',
            'REMOTE_ADDR': '127.0.0.1',
            'wsgi.url_scheme': 'http',
            'SERVER_PORT': '8080',
            'HTTP_HOST': '127.0.0.1:8080',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.input': StringIO(''),
            'CONTENT_LENGTH': '0',
            'HTTP_CONNECTION': 'keep-alive',
            'CONTENT_TYPE': ''
        }
        environ.update(kw)
        return environ

    def test_calls_setDefaultSkin(self):
        from zope.traversing.interfaces import ITraversable
        from zope.traversing.namespace import view

        class TestView:
            __name__ = 'testing'

            def __init__(self, context, request):
                pass

            def __call__(self):
                return 'foobar'

        # Define the views
        self._registerView(TestView, 'testing')

        # Bind the 'view' namespace (for @@ traversal)
        self._registerView(view, 'view', ITraversable)

        environ = self._makeEnviron(PATH_INFO='/@@testing')
        self.assertEqual(self._callFUT(environ, noopStartResponse),
                         ('', 'foobar'))

    def test_publish_can_return_new_response(self):
        from ZPublisher.HTTPRequest import HTTPRequest
        _response = DummyResponse()
        _response.body = 'BODY'
        _after1 = DummyCallable()
        _after2 = DummyCallable()
        _response.after_list = (_after1, _after2)
        environ = self._makeEnviron()
        start_response = DummyCallable()
        _publish = DummyCallable()
        _publish._result = _response
        app_iter = self._callFUT(environ, start_response, _publish)
        self.assertEqual(app_iter, ('', 'BODY'))
        (status, headers), kw = start_response._called_with
        self.assertEqual(status, '204 No Content')
        self.assertEqual(headers, [('Content-Length', '0')])
        self.assertEqual(kw, {})
        (request, module_info, repoze_tm_active), kw = _publish._called_with
        self.assertTrue(isinstance(request, HTTPRequest))
        self.assertEqual(repoze_tm_active, False)
        self.assertEqual(kw, {})
        self.assertTrue(_response._finalized)
        self.assertEqual(_after1._called_with, ((), {}))
        self.assertEqual(_after2._called_with, ((), {}))

    def test_swallows_Unauthorized(self):
        from zExceptions import Unauthorized
        environ = self._makeEnviron()
        start_response = DummyCallable()
        _publish = DummyCallable()
        _publish._raise = Unauthorized('TESTING')
        app_iter = self._callFUT(environ, start_response, _publish)
        self.assertEqual(app_iter, ('', ''))
        (status, headers), kw = start_response._called_with
        self.assertEqual(status, '401 Unauthorized')
        self.assertTrue(('Content-Length', '0') in headers)
        self.assertEqual(kw, {})

    def test_swallows_Redirect(self):
        from zExceptions import Redirect
        environ = self._makeEnviron()
        start_response = DummyCallable()
        _publish = DummyCallable()
        _publish._raise = Redirect('/redirect_to')
        app_iter = self._callFUT(environ, start_response, _publish)
        self.assertEqual(app_iter, ('', ''))
        (status, headers), kw = start_response._called_with
        self.assertEqual(status, '302 Found')
        self.assertTrue(('Location', '/redirect_to') in headers)
        self.assertTrue(('Content-Length', '0') in headers)
        self.assertEqual(kw, {})

    def test_response_body_is_file(self):

        class DummyFile(file):
            def __init__(self):
                pass

            def read(self, *args, **kw):
                raise NotImplementedError()

        _response = DummyResponse()
        _response._status = '200 OK'
        _response._headers = [('Content-Length', '4')]
        body = _response.body = DummyFile()
        environ = self._makeEnviron()
        start_response = DummyCallable()
        _publish = DummyCallable()
        _publish._result = _response
        app_iter = self._callFUT(environ, start_response, _publish)
        self.assertTrue(app_iter is body)

    def test_response_is_stream(self):
        from ZPublisher.Iterators import IStreamIterator
        from zope.interface import implements

        class TestStreamIterator(object):
            implements(IStreamIterator)
            data = "hello"
            done = 0

            def next(self):
                if not self.done:
                    self.done = 1
                    return self.data
                raise StopIteration

        _response = DummyResponse()
        _response._status = '200 OK'
        _response._headers = [('Content-Length', '4')]
        body = _response.body = TestStreamIterator()
        environ = self._makeEnviron()
        start_response = DummyCallable()
        _publish = DummyCallable()
        _publish._result = _response
        app_iter = self._callFUT(environ, start_response, _publish)
        self.assertTrue(app_iter is body)

    def test_response_is_unboundstream(self):
        from ZPublisher.Iterators import IUnboundStreamIterator
        from zope.interface import implements

        class TestUnboundStreamIterator(object):
            implements(IUnboundStreamIterator)
            data = "hello"
            done = 0

            def next(self):
                if not self.done:
                    self.done = 1
                    return self.data
                raise StopIteration

        _response = DummyResponse()
        _response._status = '200 OK'
        body = _response.body = TestUnboundStreamIterator()
        environ = self._makeEnviron()
        start_response = DummyCallable()
        _publish = DummyCallable()
        _publish._result = _response
        app_iter = self._callFUT(environ, start_response, _publish)
        self.assertTrue(app_iter is body)

    def test_request_closed_when_tm_middleware_not_active(self):
        environ = self._makeEnviron()
        start_response = DummyCallable()
        _request = DummyRequest()
        _request._closed = False

        def _close():
            _request._closed = True
        _request.close = _close

        def _request_factory(stdin, environ, response):
            return _request
        _publish = DummyCallable()
        _publish._result = DummyResponse()
        self._callFUT(environ, start_response, _publish,
                      _request_factory=_request_factory)
        self.assertTrue(_request._closed)

    def test_request_not_closed_when_tm_middleware_active(self):
        import transaction
        from ZPublisher import WSGIPublisher
        environ = self._makeEnviron()
        environ['repoze.tm.active'] = 1
        start_response = DummyCallable()
        _request = DummyRequest()
        _request._closed = False

        def _close():
            _request._closed = True
        _request.close = _close

        def _request_factory(stdin, environ, response):
            return _request
        _publish = DummyCallable()
        _publish._result = DummyResponse()
        self._callFUT(environ, start_response, _publish,
                      _request_factory=_request_factory)
        self.assertFalse(_request._closed)
        txn = transaction.get()
        self.assertTrue(
            txn in WSGIPublisher._request_closer_for_repoze_tm.requests)
        txn.commit()
        self.assertTrue(_request._closed)
        self.assertFalse(
            txn in WSGIPublisher._request_closer_for_repoze_tm.requests)
        # try again, but this time raise an exception and abort
        _request._closed = False
        _publish._raise = Exception('oops')
        self.assertRaises(Exception, self._callFUT,
                          environ, start_response, _publish,
                          _request_factory=_request_factory)
        self.assertFalse(_request._closed)
        txn = transaction.get()
        self.assertTrue(
            txn in WSGIPublisher._request_closer_for_repoze_tm.requests)
        txn.abort()
        self.assertFalse(
            txn in WSGIPublisher._request_closer_for_repoze_tm.requests)
        self.assertTrue(_request._closed)


class DummyRequest(dict):
    _processedInputs = False
    _traversed = None
    _traverse_to = None
    args = ()

    def processInputs(self):
        self._processedInputs = True

    def traverse(self, path, response=None, validated_hook=None):
        self._traversed = (path, response, validated_hook)
        return self._traverse_to


class DummyResponse(object):
    debug_mode = False
    after_list = ()
    realm = None
    _body = None
    _finalized = False
    _status = '204 No Content'
    _headers = [('Content-Length', '0')]

    def finalize(self):
        self._finalized = True
        return self._status, self._headers

    def setBody(self, body):
        self._body = body

    body = property(lambda self: self._body, setBody)


class DummyCallable(object):
    _called_with = _raise = _result = None

    def __call__(self, *args, **kw):
        self._called_with = (args, kw)
        if self._raise:
            raise self._raise
        return self._result


class DummyTM(object):
    _recorded = _raise = _result = None
    _abort = _begin = _commit = False

    def abort(self):
        self._abort = True

    def begin(self):
        self._begin = True

    def commit(self):
        self._commit = True

    def recordMetaData(self, *args):
        self._recorded = args


def noopStartResponse(status, headers):
    pass
