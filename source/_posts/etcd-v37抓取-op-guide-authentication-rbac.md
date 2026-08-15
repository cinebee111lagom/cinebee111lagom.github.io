---
title: etcd v3.7 抓取：Role-based access control
date: 2026-09-13 09:28:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/op-guide/authentication/rbac/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/op-guide/authentication/rbac/>

---

## Overview

Authentication was added in etcd 2.1. The etcd v3 API slightly modified the authentication feature’s API and user interface to better fit the new data model. This guide is intended to help users set up basic authentication and role-based access control in etcd v3.

## Special users and roles

There is one special user,
root
, and one special role,
root
.

root

### User
root

root

The
root
user, which has full access to etcd, must be created before activating authentication. The idea behind the
root
user is for administrative purposes: managing roles and ordinary users. The
root
user must have the
root
role and is allowed to change anything inside etcd.

root

### Role
root

root

The role
root
may be granted to any user, in addition to the root user. A user with the
root
role has both global read-write access and permission to update the cluster’s authentication configuration. Furthermore, the
root
role grants privileges for general cluster maintenance, including modifying cluster membership, defragmenting the store, and taking snapshots.

root

## Working with users

The
user
subcommand for
etcdctl
handles all things having to do with user accounts.

user

etcdctl

A listing of users can be found with:

```
$ etcdctl user list
```

Creating a user is as easy as

```
$ etcdctl user add myusername
```

Creating a new user will prompt for a new password. The password can be supplied from standard input when an option
--interactive=false
is given.
--new-user-password
can also be used for supplying the password.

--interactive=false

--new-user-password

Creating a user which cannot be authenticated with password is also possible like below:

```
$ etcdctl user add myusername --no-password
```

Such a user can only be
authenticated with TLS Common Name
.

etcd does not support authentication with an empty password via
--user username:
. For example, a user created with an empty password, such as
etcdctl user add anonymous:''
, cannot authenticate through username/password requests and requests such as
etcdctl --user anonymous: get foo
fail with
user name is empty
.

--user username:

etcdctl user add anonymous:''

etcdctl --user anonymous: get foo

user name is empty

Roles can be granted and revoked for a user with:

```
$ etcdctl user grant-role myusername foo
$ etcdctl user revoke-role myusername bar
```

The user’s settings can be inspected with:

```
$ etcdctl user get myusername
```

And the password for a user can be changed with

```
$ etcdctl user passwd myusername
```

Changing the password will prompt again for a new password. The password can be supplied from standard input when an option
--interactive=false
is given.

--interactive=false

Delete an account with:

```
$ etcdctl user delete myusername
```

## Working with roles

The
role
subcommand for
etcdctl
handles all things having to do with access controls for particular roles, as were granted to individual users.

role

etcdctl

List roles with:

```
$ etcdctl role list
```

Create a new role with:

```
$ etcdctl role add myrolename
```

A role has no password; it merely defines a new set of access rights.

Roles are granted access to a single key or a range of keys.

The range can be specified as an interval [start-key, end-key) where start-key should be lexically less than end-key in an alphabetical manner.

Access can be granted as either read, write, or both, as in the following examples:

```
# Give read access to a key /foo
$ etcdctl role grant-permission myrolename read /foo

# Give read access to keys with a prefix /foo/. The prefix is equal to the range [/foo/, /foo0)
$ etcdctl role grant-permission myrolename --prefix=true read /foo/

# Give write-only access to the key at /foo/bar
$ etcdctl role grant-permission myrolename write /foo/bar

# Give full access to keys in a range of [key1, key5)
$ etcdctl role grant-permission myrolename readwrite key1 key5

# Give full access to keys with a prefix /pub/
$ etcdctl role grant-permission myrolename --prefix=true readwrite /pub/
```

To see what’s granted, we can look at the role at any time:

```
$ etcdctl role get myrolename
```

Revocation of permissions is done the same logical way:

```
$ etcdctl role revoke-permission myrolename /foo/bar
```

As is removing a role entirely:

```
$ etcdctl role delete myrolename
```

## Enabling authentication

The minimal steps to enabling auth are as follows. The administrator can set up users and roles before or after enabling authentication, as a matter of preference.

Make sure the root user is created:

```
$ etcdctl user add root
Password of root:
```

Enable authentication:

```
$ etcdctl auth enable
```

After this, etcd is running with authentication enabled. To disable it for any reason, use the reciprocal command:

```
$ etcdctl --user root:rootpw auth disable
```

## Security Scope of Authentication

When authentication is enabled with
etcdctl auth enable
, it protects the V3 gRPC API operations (get, put, delete, watch, etc.).

etcdctl auth enable

The
/metrics
and
/health
HTTP endpoints operate on a separate handler and are
not
protected by V3 RBAC authentication. This design allows Prometheus and load balancers to scrape metrics without requiring gRPC authentication, while still protecting the key-value data.

/metrics

/health

To secure these observability endpoints:

Enable mTLS with
--cert-file
,
--key-file
, and
--client-cert-auth

--cert-file

--key-file

--client-cert-auth

Or bind metrics to a private interface using
--listen-metrics-urls

--listen-metrics-urls

Or use network policies/firewall rules to restrict access

## Using
etcdctl
to authenticate

etcdctl

etcdctl
supports a similar flag as
curl
for authentication.

etcdctl

curl

```
$ etcdctl --user user:password get foo
```

The password can be taken from a prompt:

```
$ etcdctl --user user get foo
```

The password can also be taken from a command line flag
--password
:

--password

```
$ etcdctl --user user --password password get foo
```

Otherwise, all
etcdctl
commands remain the same. Users and roles can still be created and modified, but require authentication by a user with the root role.

etcdctl

## Using TLS Common Name

As of version v3.2 if an etcd server is launched with the option
--client-cert-auth=true
, the field of Common Name (CN) in the client’s TLS cert will be used as an etcd user. In this case, the common name authenticates the user and the client does not need a password. Note that if both of 1.
--client-cert-auth=true
is passed and CN is provided by the client, and 2. username and password are provided by the client, the username and password based authentication is prioritized. Note that this feature cannot be used with gRPC-proxy and gRPC-gateway. This is because gRPC-proxy terminates TLS from its client so all the clients share a cert of the proxy. gRPC-gateway uses a TLS connection internally for transforming HTTP request to gRPC request so it shares the same limitation. Therefore the clients cannot provide their CN to the server correctly. gRPC-proxy will cause an error and stop if a given cert has non empty CN. gRPC-proxy returns an error which indicates that the client has an non empty CN in its cert.

--client-cert-auth=true

## Notes on password strength

The
etcdctl
and etcd API do not enforce a specific password length during user creation or user password update operations. It is the responsibility of the administrator to enforce these requirements. For avoiding security risks related to password strength,
TLS Common Name based authentication
and users created with
--no-password
option can be utilized.

etcdctl

--no-password

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Role-based access control](https://etcd.io/docs/v3.7/op-guide/authentication/rbac/)
