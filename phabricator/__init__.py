"""
python-phabricator
------------------
>>> api = phabricator.Phabricator()
>>> api.user.whoami().userName
'example'

For more endpoints, see https://secure.phabricator.com/conduit/

"""
try:
    __version__ = __import__('pkg_resources') \
        .get_distribution('phabricator').version
except:
    __version__ = 'unknown'

import collections
import copy
import hashlib
import json
import os.path
import re
import socket
import time

from ._compat import (
    MutableMapping, iteritems, string_types, httplib, urlparse, urlencode,
)


__all__ = ['Phabricator']


ON_WINDOWS = os.name == 'nt'
CURRENT_DIR = os.getcwd()


# Default Phabricator interfaces
INTERFACES = {}
with open(os.path.join(os.path.dirname(__file__), 'interfaces.json')) as fobj:
    INTERFACES = json.load(fobj)


# Load arc config
ARC_CONFIGS = (
    # System config
    os.path.join(
        os.environ['ProgramData'],
        'Phabricator',
        'Arcanist',
        'config'
    ) if ON_WINDOWS else os.path.join('/etc', 'arcconfig'),

    # User config
    os.path.join(
        os.environ['AppData'] if ON_WINDOWS else os.path.expanduser('~'),
        '.arcrc'
    ),

    # Project config
    os.path.join(CURRENT_DIR, '.arcconfig'),

    # Local project config
    os.path.join(CURRENT_DIR, '.git', 'arc', 'config'),
)

ARCRC = {}
for conf in ARC_CONFIGS:
    if os.path.exists(conf):
        with open(conf, 'r') as fobj:
            ARCRC.update(json.load(fobj))


# Map Phabricator types to Python types
PARAM_TYPE_MAP = {
    # int types
    'int': int,
    'uint': int,
    'revisionid': int,
    'revision_id': int,
    'diffid': int,
    'diff_id': int,
    'id': int,
    'enum': int,

    # bool types
    'bool': bool,

    # dict types
    'map': dict,
    'dict': dict,

    # list types
    'list': list,

    # tuple types
    'pair': tuple,

    # str types
    'str': string_types,
    'string': string_types,
    'phid': string_types,
    'guids': string_types,
    'type': string_types,
}

STR_RE = re.compile(r'([a-zA-Z_]+)')


def map_param_type(param_type):
    """
    Perform param type mapping
    This requires a bit of logic since this isn't standardized.
    If a type doesn't map, assume str
    """
    m = STR_RE.match(param_type)
    main_type = m.group(0)

    if main_type in ('list', 'array'):
        info = param_type.replace(' ', '').split('<', 1)

        # Handle no sub-type: "required list"
        sub_type = info[1] if len(info) > 1 else 'str'

        # Handle list of pairs: "optional list<pair<callsign, path>>"
        sub_match = STR_RE.match(sub_type)
        sub_type = sub_match.group(0).lower()

        return [PARAM_TYPE_MAP.setdefault(sub_type, string_types)]

    return PARAM_TYPE_MAP.setdefault(main_type, string_types)


def parse_interfaces(interfaces):
    """
    Parse the conduit.query json dict response
    This performs the logic of parsing the non-standard params dict
        and then returning a dict Resource can understand
    """
    parsed_interfaces = collections.defaultdict(dict)

    for m, d in iteritems(interfaces):
        app, func = m.split('.', 1)

        method = parsed_interfaces[app][func] = {}

        # Make default assumptions since these aren't provided by Phab
        method['formats'] = ['json', 'human']
        method['method'] = 'POST'

        method['optional'] = {}
        method['required'] = {}

        for name, type_info in iteritems(dict(d['params'])):
            # Usually in the format: <optionality> <param_type>
            info_pieces = type_info.split(' ', 1)

            # If optionality isn't specified, assume required
            if info_pieces[0] not in ('optional', 'required'):
                optionality = 'required'
                param_type = info_pieces[0]
            # Just make an optional string for "ignored" params
            elif info_pieces[0] == 'ignored':
                optionality = 'optional'
                param_type = 'string'
            else:
                optionality = info_pieces[0]
                param_type = info_pieces[1]

            # This isn't validated by the client
            if param_type.startswith('nonempty'):
                optionality = 'required'
                param_type = param_type[9:]

            method[optionality][name] = map_param_type(param_type)

    return dict(parsed_interfaces)


class InterfaceNotDefined(NotImplementedError):
    pass


class APIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return '%s: %s' % (self.code, self.message)


class InvalidAccessToken(APIError):
    pass


class Result(MutableMapping):
    def __init__(self, response):
        self.response = response

    def __getitem__(self, key):
        return self.response[key]

    __getattr__ = __getitem__

    def __setitem__(self, key, value):
        self.response[key] = value

    def __delitem__(self, key):
        del self.response[key]

    def __iter__(self):
        return iter(self.response)

    def __len__(self):
        return len(self.response.keys())

    def __repr__(self):
        return '<%s: %s>' % (type(self).__name__, repr(self.response))


class Resource(object):
    def __init__(self, api, interface=None, endpoint=None, method=None):
        self.api = api
        self.interface = interface or copy.deepcopy(parse_interfaces(INTERFACES))
        self.endpoint = endpoint
        self.method = method

    def __getattr__(self, attr):
        if attr in getattr(self, '__dict__'):
            return getattr(self, attr)
        interface = self.interface
        if attr not in interface:
            interface[attr] = {}
        return Resource(self.api, interface[attr], attr, self.endpoint)

    def __call__(self, **kwargs):
        return self._request(**kwargs)

    def _request(self, **kwargs):
        # Check for missing variables
        resource = self.interface

        def validate_kwarg(key, target):
            # Always allow list
            if isinstance(key, list):
                return all([validate_kwarg(x, target[0]) for x in key])
            return isinstance(key, tuple(target) if isinstance(target, list) else target)

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

        data = self._parse_response(response.read())

        return Result(data['result'])

    def _parse_response(self, data):
        # Process the response back to python
        parsed = self.api.formats[self.api.response_format](data)

        # Errors return 200, so check response content for exception
        if parsed['error_code']:
            raise APIError(parsed['error_code'], parsed['error_info'])

        return parsed


class Phabricator(Resource):
    formats = {
        'json': lambda x: json.loads(x),
    }

    def __init__(self, username=None, certificate=None, host=None,
            timeout=5, response_format='json', token=None, **kwargs):

        # Set values in ~/.arcrc as defaults
        if ARCRC:
            self.host = host if host else ARCRC['hosts'].keys()[0]
            if token or 'token' in ARCRC['hosts'][self.host]:
                self.token = token if token else ARCRC['hosts'][self.host]['token']
            else:
                self.username = username if username else ARCRC['hosts'][self.host]['user']
                self.certificate = certificate if certificate else ARCRC['hosts'][self.host]['cert']
        else:
            self.host = host
            self.token = token
            self.username = username
            self.certificate = certificate

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

        self.interface = parse_interfaces(interfaces)
