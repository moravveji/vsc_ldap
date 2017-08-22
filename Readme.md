# vsc_ldap

## Purpose
LDAP is a hirarchical data structure which allows to specify to which categories/groups does a member belong to. This is very useful e.g. in institutions, schools, universities, companies etc where a member of the firm is part of one or more units. At KULeuven VSC we use LDAP to organize/manage the users.

## Python-LDAP
This Python module provides basic Python facilities to talk to the local LDAP and query the users information. We use the Python-LDAP (https://www.python-ldap.org/) connector API under the hood.

## Example
As a demonstration, to retireve the list of all KULeuven users, we do the following

```python
# Get all active users
vsc = 'vsc'
search_string = '(&(status=active) (institute=leuven))'

with ldap_lib.ldap_conn(vsc) as lc:
  res = lc.search(search_string)
  n_users = len(res)

  # Get all available records of a specific field
  vsc_numbers = lc.get_field('uid')
  login = lc.get_field('instituteLogin')

  # Get a specific user info
  myself = lc.get_user_info('vsc30745')
```

Another example is to retrieve the information for a specific user from the KULeuven LDAP, knowing the user's name

```python
kuleuven = 'kuleuven'
search_string = '(uid=u0012345)'
with ldap_lib.ldap_conn(kuleuven) as lc:
  res = lc.search(search_string)
  dic = res[0][1]
  for key, val in dic.iteritems(): print key, val
```

## Specifying Connection Target
An instance of `ldap_lib.ldap_conn()` requires specifying the `target`. The `target` attribute will determine to which LDAP to connect to; therefore, the following three options are available:
+ `target=""vsc"` to query the VSC LDAP and retrieve the users information
+ `target="kuleuven"` to query the public KULeuven LDAP (u-, r- and s-accounts)
+ `target="kuleuven_private"` to query the private KULeuven LDAP (which includes the above accounts, together with the b-accounts for external users)
## Dependencies
+ Python-LDAP (https://www.python-ldap.org/)
