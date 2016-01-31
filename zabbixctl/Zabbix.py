from pyzabbix import ZabbixAPI, ZabbixAPIException
import getpass
import logging
from utils import Cache
from requests.exceptions import HTTPError, ConnectionError

#todo: don't we want an instance cache not a global one?
cache = Cache('/tmp/zabbix.cache')

log = logging.getLogger(__name__)

class ZabbixNotAuthorized(Exception):
    pass

class ZabbixError(Exception):
    pass

class Zabbix(object):

    def __init__(self, host, noverify=False, cacert=None, http=False, timeout=30):
        """
        Initializes a Zabbix instance
        :param host: hostname to connect to (ex. zabbix.yourdomain.net)
        :param noverify: turns off verification
        :param cacert: the certificate authority to use
        :param http: flag to use http over https
        :param timeout: API timeout parameter
        :return: Zabbix instance
        """
        protocol = 'http' if http is True else 'https'
        zabbix_url = '{0}://{1}/zabbix'.format(protocol, host)
        log.debug("Creating instance of Zabbic with url: %s", zabbix_url)

        self.zapi = ZabbixAPI(zabbix_url)

        if cacert is not None:
            log.debug('Setting zapi.session.verify to {0}'
                      ''.format(cacert))
            self.zapi.session.verify = cacert

        if noverify:
            log.debug('Setting zapi.session.verify to False')
            self.zapi.session.verify = False

        self.zapi.timeout = timeout
        self.fetch_zabbix_api_version()

        self.host = host
        token = cache.get(host)
        if token:
            log.debug('Found token for {0}'.format(host))
            self.zapi.auth = token
            # Let's test the token by grabbing the api version
            try:
                self.fetch_zabbix_api_version()
            except ZabbixNotAuthorized:
                self.zapi.auth = ''

    def fetch_zabbix_api_version(self):
        """
        reaches out to the zapi api info to parse the string
        :return: Version string or False
        """
        try:
            return self.zapi.apiinfo.version()

        except (HTTPError, ConnectionError, ZabbixAPIException) as e:
            # todo: cant we check by the error, not its string?
            if 'Not authorized' in str(e):
                log.debug('Token not authorized for {0}'.format(self.host))
                raise ZabbixNotAuthorized
            raise ZabbixError(e)
        raise ZabbixError('Unexpected error occured')

    def auth(self, username, password):
        """
        Performs the loggin function of the api with the supplied credentials
        :param username: username
        :param password: password
        :return: True is valid, False otherwise
        """
        try:
            self.zapi.login(username, password)
            cache.write(self.host, self.zapi.auth)
        except ZabbixAPIException as e:
            raise ZabbixNotAuthorized('Username or password invalid')
        return True


if __name__ == '__main__':
    Z_obj = Zabbix('zabbix.yourdomain.net')
    username = getpass.getuser()
    password = getpass.getpass()
    Z_obj.auth(username, password)
    import pdb
    pdb.set_trace()
