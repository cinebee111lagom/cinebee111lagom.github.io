---
title: Dragonfly 抓取：Dfdaemon
date: 2026-09-14 09:59:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/reference/commands/client/dfdaemon/>

---

A high performance P2P download daemon in Dragonfly that can download resources of different protocols.
When user triggers a file downloading task, dfdaemon will download the pieces of file from other peers.
Meanwhile, it will act as an uploader to support other peers to download pieces from it if it owns them.

## Example

### Download with Proxy

When the dfdaemon setups, it setups a HTTP proxy. Users can download traffic is proxied to P2P networks via the HTTP Proxy.

#### Download with HTTP protocol

Configure
dfdaemon.yaml
, the default path is
/etc/dragonfly/dfdaemon.yaml
,
refer to
Dfdaemon
.

Notice: set
proxy.rules.regex
to match the download path.
If the regex matches, intercepts download traffic and forwards it to the P2P network.

```
proxy
:
server
:
port
:
4001
rules
:
-
regex
:
example.*
```

```
curl -v -x 127.0.0.1:4001 http://example.com/file.txt --output /tmp/file.txt
```

#### Download with HTTPS protocol

Configure
dfdaemon.yaml
, the default path is
/etc/dragonfly/dfdaemon.yaml
,
refer to
Dfdaemon
.

Notice: set
proxy.rules.regex
to match the download path.
If the regex matches, intercepts download traffic and forwards it to the P2P network.

```
proxy
:
server
:
port
:
4001
rules
:
-
regex
:
example.*
```

Download with Insecure HTTPS protocol:

```
curl -v -x 127.0.0.1:4001 https://example.com/file.txt --insecure --output /tmp/file.txt
```

Generate a CA certificates:

```
openssl req -x509 -sha256 -days 36500 -nodes -newkey rsa:4096 -keyout ca.key -out ca.crt
```

Trust the certificate at the OS level.

Ubuntu:

```
cp ca.crt /usr/local/share/ca-certificates/ca.crt
update-ca-certificates
```

Red Hat (CentOS etc):

```
cp ca.crt /etc/pki/ca-trust/source/anchors/ca.crt
update-ca-trust
```

Configure
dfdaemon.yaml
, the default path is
/etc/dragonfly/dfdaemon.yaml
,
refer to
Dfdaemon
.

Notice: set
proxy.rules.regex
to match the download path.
If the regex matches, intercepts download traffic and forwards it to the P2P network.

```
proxy
:
server
:
port
:
4001
caCert
:
ca.crt
caKey
:
ca.key
rules
:
-
regex
:
example.*
```

Download with HTTPS protocol:

```
curl -v -x 127.0.0.1:4001 https://example.com/file.txt --output /tmp/file.txt
```

## Log

```
1. set option --console if you want to print logs to Terminal
2. log path: /var/log/dragonfly/dfdaemon/
```

---

> 完整与最新内容以官方文档为准：[Dfdaemon](https://d7y.io/docs/next/reference/commands/client/dfdaemon/)
