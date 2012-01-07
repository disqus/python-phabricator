import phabricator
import unittest
from StringIO import StringIO
from mock import patch, Mock

RESPONSES = {
    'conduit.connect': 'for(;;);{"result":{"connectionID":1759,"sessionKey":"lwvyv7f6hlzb2vawac6reix7ejvjty72svnir6zy","userPHID":"PHID-USER-6ij4rnamb2gsfpdkgmny"},"error_code":null,"error_info":null}',
    'user.whoami': 'for(;;);{"result":{"phid":"PHID-USER-6ij4rnamz2gxfpbkamny","userName":"testaccount","realName":"Test Account"},"error_code":null,"error_info":null}'
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
