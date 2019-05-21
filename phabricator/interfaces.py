import copy
import hashlib
import json
import socket
import time

from ._compatibility_maps import httplib
from ._compatibility_maps import urlparse
from ._compatibility_maps import urlencode

import phabricator.structures as st


class ConfigurationError(Exception):
    pass


class Resource(object):
    def __init__(self, api, interface=None, endpoint=None, method=None, nested=False):
        self.api = api
        self.interface = interface or copy.deepcopy(st.parse_interfaces(st.INTERFACES))
        self.endpoint = endpoint
        self.method = method
        self.nested = nested

    def __getattr__(self, attr):
        if attr in getattr(self, '__dict__'):
            return getattr(self, attr)
        interface = self.interface
        if self.nested:
            attr = "%s.%s" % (self.endpoint, attr)
        submethod_exists = False
        submethod_match = attr + '.'
        for key in interface.keys():
            if key.startswith(submethod_match):
                submethod_exists = True
                break
        if attr not in interface and submethod_exists:
            return Resource(self.api, interface, attr, self.endpoint, nested=True)
        elif attr not in interface:
            interface[attr] = {}
        if self.nested:
            return Resource(self.api, interface[attr], attr, self.method)
        return Resource(self.api, interface[attr], attr, self.endpoint)

    def __call__(self, **kwargs):
        return self._request(**kwargs)

    def _request(self, **kwargs):
        # Check for missing variables
        resource = self.interface

        def validate_kwarg(k, target):
            # Always allow list
            if isinstance(target, list):
                return (
                    isinstance(k, (list, tuple, set)) and
                    all(validate_kwarg(x, target[0]) for x in k)
                )

            return isinstance(k, tuple(target) if isinstance(target, list) else target)

        for key, val in resource.get('required', {}).items():
            if key not in [x.split(':')[0] for x in kwargs.keys()]:
                raise ValueError('Missing required argument: %s' % key)
            if isinstance(kwargs.get(key), list) and not isinstance(val, list):
                raise ValueError('Wrong argument type: %s is not a list' % key)
            elif not validate_kwarg(kwargs.get(key), val):
                if isinstance(val, list):
                    raise ValueError('Wrong argument type: %s is not a list of %ss' % (key, val[0]))
                raise ValueError('Wrong argument type: %s is not a %s' % (key, val))

        conduit = self.api._conduit

        if conduit:
            # Already authenticated, add session key to json data
            kwargs['__conduit__'] = conduit
        elif self.method == 'conduit' and self.endpoint == 'connect':
            # Not authenticated, requesting new session key
            token = str(int(time.time()))
            kwargs['authToken'] = token
            kwargs['authSignature'] = self.api.generate_hash(token)
        else:
            # Authorization is required, silently auth the user
            self.api.connect()
            kwargs['__conduit__'] = self.api._conduit

        url = urlparse.urlparse(self.api.host)
        if url.scheme == 'https':
            conn = httplib.HTTPSConnection(url.netloc, timeout=self.api.timeout)
        else:
            conn = httplib.HTTPConnection(url.netloc, timeout=self.api.timeout)

        path = url.path + '%s.%s' % (self.method, self.endpoint)

        headers = {
            'User-Agent': 'python-phabricator/%s' % str(self.api.clientVersion),
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        body = urlencode({
            "params": json.dumps(kwargs),
            "output": self.api.response_format
        })

        # TODO: Use HTTP "method" from interfaces.json
        conn.request('POST', path, body, headers)
        response = conn.getresponse()

        # Make sure we got a 2xx response indicating success
        if not response.status >= 200 or not response.status < 300:
            raise httplib.HTTPException(
                'Bad response status: {0}'.format(response.status)
            )

        response_data = response.read()
        if isinstance(response_data, str):
            response = response_data
        else:
            response = response_data.decode("utf-8")

        data = self._parse_response(response)

        return st.Result(data['result'])

    def _parse_response(self, data):
        # Process the response back to python
        parsed = self.api.formats[self.api.response_format](data)

        # Errors return 200, so check response content for exception
        if parsed['error_code']:
            raise st.APIError(parsed['error_code'], parsed['error_info'])

        return parsed


class Phabricator(Resource):
    formats = {
        'json': lambda x: json.loads(x),
    }

    def __init__(self, username=None, certificate=None, host=None,
                 timeout=5, response_format='json', token=None):

        defined_hosts = st.ARCRC.get('hosts', {})

        try:
            self.host = host if host else list(defined_hosts.keys())[0]
        except IndexError:
            raise ConfigurationError("No host found or provided.")

        current_host_config = defined_hosts.get(self.host, {})
        self.token = token if token else current_host_config.get('token')

        if self.token is None:
            self.username = username if username else current_host_config.get('user')
            self.certificate = certificate if certificate else current_host_config.get('cert')

        self.timeout = timeout
        self.response_format = response_format
        self.client = 'python-phabricator'
        self.clientVersion = 1
        self.clientDescription = socket.gethostname() + ':python-phabricator'
        self._conduit = None

        super(Phabricator, self).__init__(self)

    def _request(self, **kwargs):
        raise SyntaxError('You cannot call the Conduit API without a resource.')

    def connect(self):
        if self.token:
            self._conduit = {
                'token': self.token
            }
            return

        auth = Resource(api=self, method='conduit', endpoint='connect')

        response = auth(
            user=self.username,
            host=self.host,
            client=self.client,
            clientVersion=self.clientVersion
        )

        self._conduit = {
            'sessionKey': response.sessionKey,
            'connectionID': response.connectionID
        }

    def generate_hash(self, token):
        source_string = (token + self.api.certificate).encode('utf-8')
        return hashlib.sha1(source_string).hexdigest()

    def update_interfaces(self):
        query = Resource(api=self, method='conduit', endpoint='query')

        interfaces = query()

        self.interface = st.parse_interfaces(interfaces)
