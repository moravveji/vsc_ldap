"""
This library provides a convenient connection to the LDAP through the Python LDAP API, and 
also includes a suite of convenience methods to search the VSC LDAP, and retrieve a variety of 
information from there. 

Example: If we want to retrieve the vsc numbers of the inactive Leuven users, we do the following:

>>>from vsc_ldap import ldap_lib
>>>search_string = '(&(status=inactive) (institute=leuven))'
>>>target = 'vsc'
>>>with ldap_lib.ldap_conn(target) as lc:
>>>  result = lc.search(search_string)
>>>  vsc_numbers = lc.get_field(field='uid')
"""

import sys, os
import logging
import ldap

###########################################################
logger = logging.getLogger(__name__)
###########################################################
class ldap_conn(object):
  """ A class that provides a connection to the local VSC LDAP at Leuven """

  def __init__(self, target):
    """ 
    Constructor.
    Many of the connection arguments/options that are needed for a secure binding are
    hardcoded as attributes of the class, e.g. uri, who, cred, etc. 
    """
    # target is either "leuven" or "vsc"
    self.target = target
    self.conf_file = os.path.dirname(__file__) + '/private.conf'
    self.set_connection_phrases()

    # Set the search scope to entire subtree
    self.scope = ldap.SCOPE_SUBTREE

    # Control flags
    self.is_initialized = False
    self.is_bound = False

    # Connector: set by initialize()
    self.conn = None 

    # Search results
    self.filterstr = ''
    self.search_id = None
    self.result_type = None
    self.result = []

    # Manage the output results
    self.results_managed = False

  #------------------------------------
  def set_connection_phrases(self):
    """
    Assign the correct uri and base for the connection, based on the specified target
    Reference to each of the items:
    - uri: /apps/leuven/icts/icts-services/prod/conf/ldap.conf
    - base: /apps/leuven/icts/icts-services/prod/conf/ldap.conf
    - who: /apps/leuven/icts/vsc-scripts/perl/ldap_utils.mp
    - cred: /apps/leuven/icts/cgi.passwd
    """ 
    target = self.target
    dic = self._read_config_file()
   
    # The LDAP configs sit in the following file: 
    # taken from "less $VSC_CONF"
    if target == 'kuleuven':
      self.uri   = dic['kul_uri'] 
      self.base = dic['kul_base']
      self.who  = dic['kul_who']
      self.cred  = dic['kul_cred']
    elif target == 'vsc':
      self.uri   = dic['vsc_uri']
      self.base = dic['vsc_base']
      self.who = dic['vsc_who']
      self.cred = dic['vsc_cred']
    else:
      logger.error('set_connection_phrases: Unrecognised target: {0}'.format(target))
      sys.exit(1)

  #------------------------------------
  def _read_config_file(self):
    """ 
    Read the private configure file 
    @return: the connection configurations for the KULeuven and VSC LDAPs.
    @rtype: dict
    """
    if not os.path.exists(self.conf_file):
      logger.error('_read_config_file: Could not find the config file {0}'.format(self.conf_file))
      sys.exit(1)  
    dic = dict()
    with open(self.conf_file, 'r') as r: lines = r.readlines()
    for line in lines:
      row = line.rstrip('\r\n').split()
      key, val = row[0], row[-1]
      if val == 'None': val = ''
      dic[key] = val
    
    return dic 

  #------------------------------------
  def __enter__(self):
    """ Upon entering, initialize the ldap connection, and set the self.conn attribute """
    try: 
      self.initialize()
    except:
      logger.error('__enter__: calling initialize() method failed')
      sys.exit(1)

    try:
      self.bind()
    except:
      logger.error('__enter__: calling bind() method failed')
      sys.exit(1)
 
    return self
  #------------------------------------
  def __exit__(self, type, value, tb):
     """ Upon exiting, close/unbind the connection """
     self.conn.unbind_s()

  #------------------------------------
  def get(self, attr):
    """ The getter method """
    if not hasattr(self, attr):
      logger.error('get: attribute {0} is undefined'.format(attr))
      sys.exit(1)
    
    return getattr(self, attr)

  #------------------------------------
  def setter(self, attr, val):
    """  The setter method """
    if not hasattr(self, attr):
      logger.error('setter: attribute {0} is undefined'.format(attr))
      sys.exit(1)

    setattr(self, attr, val)    

  #------------------------------------
  # Extra Methods
  #------------------------------------
  def initialize(self):
    """ Initialize the LDAP connection """ 
    try:
      self.conn = ldap.initialize(uri=self.uri)
      self.conn.protocol_version = ldap.VERSION3
      self.conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
      self.conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
      self.is_initialized = True
    except ldap.LDAPError as err:
      self.is_initialized = False
      logger.error(err.desc)
      sys.exit(1)

  #------------------------------------
  def bind(self):
    """ A wrapper around the ldap.bind() method """
    if not self.is_initialized:
      logger.error('bind: connection is not initialized!')
      sys.exit(1)

    try:
      res_bind = self.conn.simple_bind(who=self.who, cred=self.cred)
      self.is_bound = True
    except ldap.LDAPError as err:
      self.is_bound = False
      print type(err)
      logger.error('bind: failed: {0}'.format(err))
      sys.exit(1)

  #------------------------------------
  def search(self, filterstr):
    """  
    A wrapper around the ldap.search() and ldap.result() methods, carrying out the search operation and
    returning the output result.
    @param filterstr: The filter string -- or better said, the search string -- to query the LDAP.
    @type filterstr: str
    @return: the self.search_id is assigned to the result of the conn.search(), and then the _get_result()
                    method is called to allocate the self.result attribute to the list of output results. In return, 
                    self.result is returned back
    @rtype: list
    """
    if not self.is_bound:
      logger.warning('search: trying to bind() first ...')
      self.bind()

    self.filterstr = filterstr
    self.search_id = self.conn.search(base=self.base, scope=self.scope, filterstr=self.filterstr)
    self._get_result()

    return self.result

  #------------------------------------
  def _get_result(self):
    """ 
    Achtung: Private method!
    A wrapper around the ldap.result() method 
    if self.search() is already called, the self.search_id is used to fetch all available results as a list
    @return: all results are fetched, and the follwoing three class attributes are also set:
                    - result_type (int)
                    - result (list)
    @rtype: list
    """
    if self.search_id is None:
      logger.warning('get_result: no search() is done yet! returning empty list')
      return []

    self.result_type, self.result = self.conn.result(msgid=self.search_id, all=1)

  #------------------------------------
  def get_field(self, field):
     """ 
     The self.result contains a list of tuples (dn, data). The data is a dictionary with the following keys:
     
     'status', 'scratchDirectory', 'dataDirectory', 'cn', 'homeQuota', 'objectClass', 'loginShell', 'homeDirectory',
     'uidNumber', 'researchField', 'institute', 'gidNumber', 'gecos', 'dataQuota', 'mukHomeOnScratch', 'mail',
     'scratchQuota', 'pubkey', 'instituteLogin', 'uid'
     
     This method returns a list of results for a given field

     @param key: the key used to retrieve the information
     @type key: str
     @return:
     @rtype:
     """
     if not self.result: return None

     res = self.result
     first = res[0]
     dn, data = first
     keys = data.keys()
     if field not in keys:
       logger.error('get_item: the requested field {0} is unavailable'.format(field))
       sys.exit(1)
     
     return [tup[1][field][0] for tup in res]
     
  #------------------------------------
  def get_user_info(self, vsc):
    """
    Retrieve the entire information from LDAP for the user, specifying the user's vsc number, e.g. vsc12345.

    @param vsc: the user's vsc number
    @type vsc: str
    @return: dictionary of the entire available user information. The returned dictionary has the following keys:
                   'status', 'scratchDirectory', 'dataDirectory', 'cn', 'homeQuota', 'objectClass', 'loginShell', 'homeDirectory',
                   'uidNumber', 'researchField', 'institute', 'gidNumber', 'gecos', 'dataQuota', 'mukHomeOnScratch', 'mail',
                   'scratchQuota', 'pubkey', 'instituteLogin', 'uid'
    @rtype: dict
    """
    if not self.result: return None
    
    res    = self.result
    users = self.get_field('uid') #[tup[1]['uid'] for tup in res]
    try:
      ind = users.index(vsc)
      return res[ind][1]
    except ValueError:
      logger.warning('get_user_info: Could not find the user: {0}'.format(vsc))
      return None

  #------------------------------------
  #------------------------------------

###########################################################
###########################################################

