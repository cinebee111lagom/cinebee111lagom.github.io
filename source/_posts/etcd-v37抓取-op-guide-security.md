---
title: etcd v3.7 抓取：Transport security model
date: 2026-09-13 09:30:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/op-guide/security/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/op-guide/security/>

---

etcd supports automatic TLS as well as authentication through client certificates for both clients to server as well as peer (server to server / cluster) communication.
Note that etcd doesn’t enable
RBAC based authentication
or the authentication feature in the transport layer by default to reduce friction for users getting started with the database. Further, changing this default would be a breaking change for the project which was established since 2013. An etcd cluster which doesn’t enable security features can expose its data to any clients.

To get up and running, first have a CA certificate and a signed key pair for one member. It is recommended to create and sign a new key pair for every member in a cluster.

For convenience, the
cfssl
tool provides an easy interface to certificate generation, and we provide an example using the tool
here
. Alternatively, try this
guide to generating self-signed key pairs
.

The list of flags provided below may not be up-to-date due to ongoing development changes. For the latest available flags, run
etcd --help
or refer to the
etcd help
.

etcd --help

## Basic setup

etcd takes several certificate related configuration options, either through command-line flags or environment variables:

Client-to-server communication:

--cert-file=<path>
: Certificate used for SSL/TLS connections
to
etcd. When this option is set, advertise-client-urls can use the HTTPS schema.

--cert-file=<path>

--key-file=<path>
: Key for the certificate. Must be unencrypted.

--key-file=<path>

--client-cert-auth
: When this is set etcd will check all incoming HTTPS requests for a client certificate signed by the trusted CA, requests that don’t supply a valid client certificate will fail. If
authentication
is enabled, the certificate provides credentials for the user name given by the Common Name field.

--client-cert-auth

--trusted-ca-file=<path>
: Trusted certificate authority.

--trusted-ca-file=<path>

--auto-tls
: Use automatically generated self-signed certificates for TLS connections with clients.

--auto-tls

Peer (server-to-server / cluster) communication:

The peer options work the same way as the client-to-server options:

--peer-cert-file=<path>
: Certificate used for SSL/TLS connections between peers. This will be used both for listening on the peer address as well as sending requests to other peers.

--peer-cert-file=<path>

--peer-key-file=<path>
: Key for the certificate. Must be unencrypted.

--peer-key-file=<path>

--peer-client-cert-auth
: When set, etcd will check all incoming peer requests from the cluster for valid client certificates signed by the supplied CA.

--peer-client-cert-auth

--peer-trusted-ca-file=<path>
: Trusted certificate authority.

--peer-trusted-ca-file=<path>

--peer-auto-tls
: Use automatically generated self-signed certificates for TLS connections between peers.

--peer-auto-tls

If either a client-to-server or peer certificate is supplied the key must also be set. All of these configuration options are also available through the environment variables,
ETCD_CA_FILE
,
ETCD_PEER_CA_FILE
and so on.

ETCD_CA_FILE

ETCD_PEER_CA_FILE

Common options:

--cipher-suites
: Comma-separated list of supported TLS cipher suites between server/client and peers (empty will be auto-populated by Go).

--cipher-suites

--tls-min-version=<version>
Sets the minimum TLS version supported by etcd.

--tls-min-version=<version>

--tls-max-version=<version>
Sets the maximum TLS version supported by etcd. If not set the maximum version supported by Go will be used.

--tls-max-version=<version>

### TLS certificate keyUsage and extendedKeyUsage

When generating X.509 certificates for securing etcd transport,
certificates should include appropriate
keyUsage
and
extendedKeyUsage
fields depending on their role. etcd relies on Go’s
crypto/tls
and
crypto/x509
libraries for certificate verification,
which enforce these usages during the TLS handshake.

keyUsage

extendedKeyUsage

crypto/tls

crypto/x509

The following table summarizes the recommended usages for common certificate roles:

Notes:

When
--peer-client-cert-auth
is enabled, peer certificates are
used for mutual TLS between etcd members and therefore require both
serverAuth
and
clientAuth
.

--peer-client-cert-auth

serverAuth

clientAuth

Client certificates used with
--client-cert-auth
should include
clientAuth
.

--client-cert-auth

clientAuth

## Example 1: Client-to-server transport security with HTTPS

For this, have a CA certificate (
ca.crt
) and signed key pair (
server.crt
,
server.key
) ready.

ca.crt

server.crt

server.key

Let us configure etcd to provide simple HTTPS transport security step by step:

```
$ etcd --name infra0 --data-dir infra0
\
--cert-file
=
/path/to/server.crt --key-file
=
/path/to/server.key
\
--advertise-client-urls
=
https://127.0.0.1:2379 --listen-client-urls
=
https://127.0.0.1:2379
```

This should start up fine and it will be possible to test the configuration by speaking HTTPS to etcd:

```
$ curl --cacert /path/to/ca.crt https://127.0.0.1:2379/v2/keys/foo -XPUT -d
value
=
bar -v
```

The command should show that the handshake succeed. Since we use self-signed certificates with our own certificate authority, the CA must be passed to curl using the
--cacert
option. Another possibility would be to add the CA certificate to the system’s trusted certificates directory (usually in
/etc/pki/tls/certs
or
/etc/ssl/certs
).

--cacert

/etc/pki/tls/certs

/etc/ssl/certs

OSX 10.9+ Users
: curl 7.30.0 on OSX 10.9+ doesn’t understand certificates passed in on the command line.
Instead, import the dummy ca.crt directly into the keychain or add the
-k
flag to curl to ignore errors.
To test without the
-k
flag, run
open ./tests/fixtures/ca/ca.crt
and follow the prompts.
Please remove this certificate after testing!
If there is a workaround, let us know.

-k

open ./tests/fixtures/ca/ca.crt

## Example 2: Client-to-server authentication with HTTPS client certificates

For now we’ve given the etcd client the ability to verify the server identity and provide transport security. We can however also use client certificates to prevent unauthorized access to etcd.

The clients will provide their certificates to the server and the server will check whether the cert is signed by the supplied CA and decide whether to serve the request.

The same files mentioned in the first example are needed for this, as well as a key pair for the client (
client.crt
,
client.key
) signed by the same certificate authority.

client.crt

client.key

```
$ etcd --name infra0 --data-dir infra0
\
--client-cert-auth --trusted-ca-file
=
/path/to/ca.crt --cert-file
=
/path/to/server.crt --key-file
=
/path/to/server.key
\
--advertise-client-urls https://127.0.0.1:2379 --listen-client-urls https://127.0.0.1:2379
```

Now try the same request as above to this server:

```
$ curl --cacert /path/to/ca.crt https://127.0.0.1:2379/v2/keys/foo -XPUT -d
value
=
bar -v
```

The request should be rejected by the server:

```
...
routines:SSL3_READ_BYTES:sslv3 alert bad certificate
...
```

To make it succeed, we need to give the CA signed client certificate to the server:

```
$ curl --cacert /path/to/ca.crt --cert /path/to/client.crt --key /path/to/client.key
\
-L https://127.0.0.1:2379/v2/keys/foo -XPUT -d
value
=
bar -v
```

The output should include:

```
...
SSLv3, TLS handshake, CERT verify (15):
...
TLS handshake, Finished (20)
```

And also the response from the server:

```
{
"action"
:
"set"
,
"node"
:
{
"createdIndex"
:
12
,
"key"
:
"/foo"
,
"modifiedIndex"
:
12
,
"value"
:
"bar"
}
}
```

Specify cipher suites to block
weak TLS cipher suites
.

TLS handshake would fail when client hello is requested with invalid cipher suites.

For instance:

```
$ etcd
\
--cert-file ./server.crt
\
--key-file ./server.key
\
--trusted-ca-file ./ca.crt
\
--cipher-suites TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
```

Then, client requests must specify one of the cipher suites specified in the server:

```
# valid cipher suite
$ curl
\
--cacert /path/to/ca.crt
\
--cert /path/to/client.crt
\
--key /path/to/client.key
\
-L
[
CLIENT-URL
]
/metrics
\
--ciphers ECDHE-RSA-AES128-GCM-SHA256
# request succeeds
etcd_server_version
{
server_version
=
"3.2.22"
}
1
...
```

```
# invalid cipher suite
$ curl
\
--cacert /path/to/ca.crt
\
--cert /path/to/client.crt
\
--key /path/to/client.key
\
-L
[
CLIENT-URL
]
/metrics
\
--ciphers ECDHE-RSA-DES-CBC3-SHA
# request fails with
(
35
)
error:14094410:SSL routines:ssl3_read_bytes:sslv3 alert handshake failure
```

## Example 3: Transport security & client certificates in a cluster

etcd supports the same model as above for
peer communication
, that means the communication between etcd members in a cluster.

Assuming we have our
ca.crt
and two members with their own key pairs (
member1.crt
&
member1.key
,
member2.crt
&
member2.key
) signed by this CA, we launch etcd as follows:

ca.crt

member1.crt

member1.key

member2.crt

member2.key

```
DISCOVERY_URL
=
...
# from https://discovery.etcd.io/new
# member1
$ etcd --name infra1 --data-dir infra1
\
--peer-client-cert-auth --peer-trusted-ca-file
=
/path/to/ca.crt --peer-cert-file
=
/path/to/member1.crt --peer-key-file
=
/path/to/member1.key
\
--initial-advertise-peer-urls
=
https://10.0.1.10:2380 --listen-peer-urls
=
https://10.0.1.10:2380
\
--discovery
${
DISCOVERY_URL
}
# member2
$ etcd --name infra2 --data-dir infra2
\
--peer-client-cert-auth --peer-trusted-ca-file
=
/path/to/ca.crt --peer-cert-file
=
/path/to/member2.crt --peer-key-file
=
/path/to/member2.key
\
--initial-advertise-peer-urls
=
https://10.0.1.11:2380 --listen-peer-urls
=
https://10.0.1.11:2380
\
--discovery
${
DISCOVERY_URL
}
```

The etcd members will form a cluster and all communication between members in the cluster will be encrypted and authenticated using the client certificates. The output of etcd will show that the addresses it connects to use HTTPS.

## Example 4: Automatic self-signed transport security

When you specify ClientAutoTLS and PeerAutoTLS, the validity period of the client certificate and peer certificate automatically generated by etcd is only 1 year. You can specify the --self-signed-cert-validity flag to set the validity period of the certificate in years.

For cases where communication encryption, but not authentication, is needed, etcd supports encrypting its messages with automatically generated self-signed certificates. This simplifies deployment because there is no need for managing certificates and keys outside of etcd.
Configure etcd to use self-signed certificates for client and peer connections with the flags
--auto-tls
and
--peer-auto-tls
:

--auto-tls

--peer-auto-tls

```
DISCOVERY_URL
=
...
# from https://discovery.etcd.io/new
# member1
$ etcd --name infra1 --data-dir infra1
\
--auto-tls --peer-auto-tls
\
--initial-advertise-peer-urls
=
https://10.0.1.10:2380 --listen-peer-urls
=
https://10.0.1.10:2380
\
--discovery
${
DISCOVERY_URL
}
# member2
$ etcd --name infra2 --data-dir infra2
\
--auto-tls --peer-auto-tls
\
--initial-advertise-peer-urls
=
https://10.0.1.11:2380 --listen-peer-urls
=
https://10.0.1.11:2380
\
--discovery
${
DISCOVERY_URL
}
```

Self-signed certificates do not authenticate identity so curl will return an error:

```
curl:
(
60
)
SSL certificate problem: Invalid certificate chain
```

To disable certificate chain checking, invoke curl with the
-k
flag:

-k

```
$ curl -k https://127.0.0.1:2379/v2/keys/foo -Xput -d
value
=
bar -v
```

## Notes for DNS SRV


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Transport security model](https://etcd.io/docs/v3.7/op-guide/security/)
