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


import phabricator


RESPONSES = {
    'conduit.connect': '{"result":{"connectionID":1759,"sessionKey":"lwvyv7f6hlzb2vawac6reix7ejvjty72svnir6zy","userPHID":"PHID-USER-6ij4rnamb2gsfpdkgmny"},"error_code":null,"error_info":null}',
    'user.whoami': '{"result":{"phid":"PHID-USER-6ij4rnamz2gxfpbkamny","userName":"testaccount","realName":"Test Account"},"error_code":null,"error_info":null}',
    'maniphest.find': '{"result":{"PHID-TASK-4cgpskv6zzys6rp5rvrc":{"id":"722","phid":"PHID-TASK-4cgpskv6zzys6rp5rvrc","authorPHID":"PHID-USER-5022a9389121884ab9db","ownerPHID":"PHID-USER-5022a9389121884ab9db","ccPHIDs":["PHID-USER-5022a9389121884ab9db","PHID-USER-ba8aeea1b3fe2853d6bb"],"status":"3","priority":"Needs Triage","title":"Relations should be two-way","description":"When adding a differential revision you can specify Maniphest Tickets to add the relation. However, this doesnt add the relation from the ticket -> the differently.(This was added via the commit message)","projectPHIDs":["PHID-PROJ-358dbc2e601f7e619232","PHID-PROJ-f58a9ac58c333f106a69"],"uri":"https:\/\/secure.phabricator.com\/T722","auxiliary":[],"objectName":"T722","dateCreated":"1325553508","dateModified":"1325618490"}},"error_code":null,"error_info":null}'
}

CERTIFICATE = (
    'fdhcq3zsyijnm4h6gmh43zue5umsmng5t4dlwodvmiz4cnc6fl6f'
    'zrvjbfg2ftktrcddan7b3xtgmfge2afbrh4uwam6pfxpq5dbkhbl'
    '6mgaijdzpq5efw2ynlnjhoeqyh6dakl4yg346gbhabzkcxreu7hc'
    'jhw6vo6wwa7ky2sjdk742khlgsakwtme6sr2dfkhlxxkcqw3jngy'
    'rq5zj7m6m7hnscuzlzsviawnvg47pe7l4hxiexpbb5k456r'
)

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
        mock_obj.getresponse.return_value = StringIO(RESPONSES['conduit.connect'])
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
        mock_obj.getresponse.return_value = StringIO(RESPONSES['maniphest.find'])
        mock_obj.getresponse.return_value.status = 200

        api = phabricator.Phabricator(username='test', certificate='test', host='http://localhost')
        api._conduit = True

        result = api.maniphest.find(ownerphids=['PHID-USER-5022a9389121884ab9db'])
        self.assertEqual(len(result), 1)

        # Test iteration
        self.assertIsInstance([x for x in result], list)

        # Test getattr
        self.assertEqual(result['PHID-TASK-4cgpskv6zzys6rp5rvrc']['status'], '3')

    def test_validation(self):
        self.api._conduit = True

        self.assertRaises(ValueError, self.api.differential.find)
        with self.assertRaises(ValueError):
            self.api.differential.find(query=1)
        with self.assertRaises(ValueError):
            self.api.differential.find(query='1')
        with self.assertRaises(ValueError):
            self.api.differential.find(query='1', guids='1')


if __name__ == '__main__':
    unittest.main()
