"""
python-phabricator
------------------
>>> from phabricator import Phabricator
>>> api = Phabricator()
>>> api.user.whoami().userName
'example'

For more endpoints, see https://secure.phabricator.com/conduit/
"""
import collections
import json
import os.path
import re

from ._compatibility_maps import MutableMapping
from ._compatibility_maps import iteritems
from ._compatibility_maps import string_types


ON_WINDOWS = os.name == 'nt'
CURRENT_DIR = os.getcwd()


# Default Phabricator interfaces
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

TYPE_INFO_COMMENT_RE = re.compile(r'\s*\([^)]+\)\s*$')
TYPE_INFO_SPLITTER_RE = re.compile(r'(\w+(?:<.+>)?)(?:\s+|$)')
TYPE_INFO_RE = re.compile(r'<?(\w+)(<[^>]+>>?)?(?:.+|$)')


def map_param_type(param_type):
    """
    Perform param type mapping
    This requires a bit of logic since this isn't standardized.
    If a type doesn't map, assume str
    """
    main_type, sub_type = TYPE_INFO_RE.match(param_type).groups()

    if main_type in ('list', 'array'):
        # Handle no sub-type: "required list"
        if sub_type is not None:
            sub_type = sub_type.strip()

        if not sub_type:
            sub_type = 'str'

        # Handle list of pairs: "optional list<pair<callsign, path>>"
        sub_match = TYPE_INFO_RE.match(sub_type)
        if sub_match:
            sub_type = sub_match.group(1).lower()

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
            # Set the defaults
            optionality = 'required'
            param_type = 'string'

            # Usually in the format: <optionality> <param_type>
            type_info = TYPE_INFO_COMMENT_RE.sub('', type_info)
            info_pieces = TYPE_INFO_SPLITTER_RE.findall(type_info)
            for info_piece in info_pieces:
                if info_piece in ('optional', 'required'):
                    optionality = info_piece
                elif info_piece == 'ignored':
                    optionality = 'optional'
                    param_type = 'string'
                elif info_piece == 'nonempty':
                    optionality = 'required'
                elif info_piece == 'deprecated':
                    optionality = 'optional'
                else:
                    param_type = info_piece

            method[optionality][name] = map_param_type(param_type)

    return dict(parsed_interfaces)


class APIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return '%s: %s' % (self.code, self.message)


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
        return len(self.response)

    def __repr__(self):
        return '<%s: %s>' % (type(self).__name__, repr(self.response))
