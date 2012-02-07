import phabricator
import unittest
from StringIO import StringIO
from mock import patch, Mock

RESPONSES = {
    'conduit.connect': 'for(;;);{"result":{"connectionID":1759,"sessionKey":"lwvyv7f6hlzb2vawac6reix7ejvjty72svnir6zy","userPHID":"PHID-USER-6ij4rnamb2gsfpdkgmny"},"error_code":null,"error_info":null}',
    'user.whoami': 'for(;;);{"result":{"phid":"PHID-USER-6ij4rnamz2gxfpbkamny","userName":"testaccount","realName":"Test Account"},"error_code":null,"error_info":null}',
    'maniphest.find': 'for(;;);{"result":{"PHID-TASK-4cgpskv6zzys6rp5rvrc":{"id":"722","phid":"PHID-TASK-4cgpskv6zzys6rp5rvrc","authorPHID":"PHID-USER-5022a9389121884ab9db","ownerPHID":"PHID-USER-5022a9389121884ab9db","ccPHIDs":["PHID-USER-5022a9389121884ab9db","PHID-USER-ba8aeea1b3fe2853d6bb"],"status":"3","priority":"Needs Triage","title":"Relations should be two-way","description":"When adding a differential revision you can specify Maniphest Tickets to add the relation. However, this doesnt add the relation from the ticket -> the differently.(This was added via the commit message)","projectPHIDs":["PHID-PROJ-358dbc2e601f7e619232","PHID-PROJ-f58a9ac58c333f106a69"],"uri":"https:\/\/secure.phabricator.com\/T722","auxiliary":[],"objectName":"T722","dateCreated":"1325553508","dateModified":"1325618490"}},"error_code":null,"error_info":null}'
}

class PhabricatorTest(unittest.TestCase):
    def setUp(self):
        self.api = phabricator.Phabricator(username='test', certificate='test', host='http://localhost')
        self.api.certificate = "fdhcq3zsyijnm4h6gmh43zue5umsmng5t4dlwodvmiz4cnc6fl6f" + \
                               "zrvjbfg2ftktrcddan7b3xtgmfge2afbrh4uwam6pfxpq5dbkhbl" + \
                               "6mgaijdzpq5efw2ynlnjhoeqyh6dakl4yg346gbhabzkcxreu7hc" + \
                               "jhw6vo6wwa7ky2sjdk742khlgsakwtme6sr2dfkhlxxkcqw3jngy" + \
                               "rq5zj7m6m7hnscuzlzsviawnvg47pe7l4hxiexpbb5k456r"

    def test_generate_hash(self):
        token = '12345678'
        hashed = self.api.generate_hash(token)
        self.assertEquals(hashed, 'f8d3bea4e58a2b2967d93d5b307bfa7c693b2e7f')

    @patch('phabricator.httplib.HTTPConnection')
    def test_connect(self, mock_connection):
        mock = mock_connection.return_value = Mock()
        mock.getresponse.return_value = StringIO(RESPONSES['conduit.connect'])

        api = phabricator.Phabricator(username='test', certificate='test', host='http://localhost')
        api.connect()
        self.assertTrue('sessionKey' in api.conduit.keys())
        self.assertTrue('connectionID' in api.conduit.keys())

    @patch('phabricator.httplib.HTTPConnection')
    def test_user_whoami(self, mock_connection):
        mock = mock_connection.return_value = Mock()
        mock.getresponse.return_value = StringIO(RESPONSES['user.whoami'])

        api = phabricator.Phabricator(username='test', certificate='test', host='http://localhost')
        api.conduit = True

        self.assertEqual('testaccount', api.user.whoami()['userName'])

    @patch('phabricator.httplib.HTTPConnection')
    def test_maniphest_find(self, mock_connection):
        mock = mock_connection.return_value = Mock()
        mock.getresponse.return_value = StringIO(RESPONSES['maniphest.find'])

        api = phabricator.Phabricator(username='test', certificate='test', host='http://localhost')
        api.conduit = True

        result = api.maniphest.find(ownerphids=["PHID-USER-5022a9389121884ab9db"])
        self.assertEqual(1, len(result))

        # Test iteration
        self.assertTrue(isinstance([x for x in result], list))

        # Test getattr
        self.assertEqual("3", result["PHID-TASK-4cgpskv6zzys6rp5rvrc"]["status"])

    def test_validation(self):
        self.api.conduit = True

        with self.assertRaises(ValueError):
            self.assertRaises(ValueError, self.api.differential.find())
            self.assertRaises(ValueError, self.api.differential.find(query=1))
            self.assertRaises(ValueError, self.api.differential.find(query="1"))
            self.assertRaises(ValueError, self.api.differential.find(query="1", guids="1"))
            self.assertRaises(ValueError, self.api.differential.find(query="1", guids=["1"]))


if __name__ == '__main__':
    unittest.main()
