try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import unittest.mock as mock
except ImportError:
    import mock

from pkg_resources import resource_string
import json

import phabricator


RESPONSES = json.loads(
    resource_string(
        'phabricator.tests.resources',
        'responses.json'
    ).decode('utf8')
)
CERTIFICATE = resource_string(
    'phabricator.tests.resources',
    'certificate.txt'
).decode('utf8').strip()


# Protect against local user's .arcrc interference.
phabricator.ARCRC = {}


class PhabricatorTest(unittest.TestCase):
    def setUp(self):
        self.api = phabricator.Phabricator(
            username='test',
            certificate='test',
            host='http://localhost'
        )
        self.api.certificate = CERTIFICATE

    def test_generate_hash(self):
        token = '12345678'
        hashed = self.api.generate_hash(token)
        self.assertEqual(hashed, 'f8d3bea4e58a2b2967d93d5b307bfa7c693b2e7f')

    @mock.patch('phabricator.httplib.HTTPConnection')
    def test_connect(self, mock_connection):
        mock_obj = mock_connection.return_value = mock.Mock()
        mock_obj.getresponse.return_value = StringIO(
            RESPONSES['conduit.connect']
        )
        mock_obj.getresponse.return_value.status = 200

        api = phabricator.Phabricator(
            username='test',
            certificate='test',
            host='http://localhost'
        )

        api.connect()
        keys = api._conduit.keys()
        self.assertIn('sessionKey', keys)
        self.assertIn('connectionID', keys)

    @mock.patch('phabricator.httplib.HTTPConnection')
    def test_user_whoami(self, mock_connection):
        mock_obj = mock_connection.return_value = mock.Mock()
        mock_obj.getresponse.return_value = StringIO(RESPONSES['user.whoami'])
        mock_obj.getresponse.return_value.status = 200

        api = phabricator.Phabricator(
            username='test',
            certificate='test',
            host='http://localhost'
        )
        api._conduit = True

        self.assertEqual(api.user.whoami()['userName'], 'testaccount')

    def test_classic_resources(self):
        api = phabricator.Phabricator(
            username='test',
            certificate='test',
            host='http://localhost'
        )

        self.assertEqual(api.user.whoami.method, 'user')
        self.assertEqual(api.user.whoami.endpoint, 'whoami')

    def test_nested_resources(self):
        api = phabricator.Phabricator(
            username='test',
            certificate='test',
            host='http://localhost'
        )

        self.assertEqual(api.diffusion.repository.edit.method, 'diffusion')
        self.assertEqual(api.diffusion.repository.edit.endpoint, 'repository.edit')

    @mock.patch('phabricator.httplib.HTTPConnection')
    def test_bad_status(self, mock_connection):
        mock_obj = mock_connection.return_value = mock.Mock()
        mock_obj.getresponse.return_value = mock.Mock()
        mock_obj.getresponse.return_value.status = 400

        api = phabricator.Phabricator(
                username='test',
                certificate='test',
                host='http://localhost'
        )
        api._conduit = True

        with self.assertRaises(phabricator.httplib.HTTPException):
            api.user.whoami()

    @mock.patch('phabricator.httplib.HTTPConnection')
    def test_maniphest_find(self, mock_connection):
        mock_obj = mock_connection.return_value = mock.Mock()
        mock_obj.getresponse.return_value = StringIO(
            RESPONSES['maniphest.find']
        )
        mock_obj.getresponse.return_value.status = 200

        api = phabricator.Phabricator(
            username='test',
            certificate='test',
            host='http://localhost'
        )
        api._conduit = True

        result = api.maniphest.find(
            ownerphids=['PHID-USER-5022a9389121884ab9db']
        )
        self.assertEqual(len(result), 1)

        # Test iteration
        self.assertIsInstance([x for x in result], list)

        # Test getattr
        self.assertEqual(
            result['PHID-TASK-4cgpskv6zzys6rp5rvrc']['status'],
            '3'
        )

    def test_validation(self):
        self.api._conduit = True

        self.assertRaises(ValueError, self.api.differential.find)
        with self.assertRaises(ValueError):
            self.api.differential.find(query=1)
        with self.assertRaises(ValueError):
            self.api.differential.find(query='1')
        with self.assertRaises(ValueError):
            self.api.differential.find(query='1', guids='1')

    def test_map_param_type(self):
        uint = 'uint'
        self.assertEqual(phabricator.map_param_type(uint), int) 

        list_bool = 'list<bool>'
        self.assertEqual(phabricator.map_param_type(list_bool), [bool]) 

        list_pair = 'list<pair<callsign, path>>'
        self.assertEqual(phabricator.map_param_type(list_pair), [tuple]) 

        complex_list_pair = 'list<pair<string-constant<"gtcm">, string>>'
        self.assertEqual(phabricator.map_param_type(complex_list_pair), [tuple])

if __name__ == '__main__':
    unittest.main()
