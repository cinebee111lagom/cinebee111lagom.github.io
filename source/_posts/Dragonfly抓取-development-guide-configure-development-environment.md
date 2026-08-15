---
title: Dragonfly 抓取：Configure the Development Environment
date: 2026-09-14 10:06:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/development-guide/configure-development-environment/>

---

This document describes how to configure a local development environment for Dragonfly.

## Prerequisites

## Clone Dragonfly

Clone the source code of Dragonfly:

```
git clone --recurse-submodules https://github.com/dragonflyoss/dragonfly.git
cd dragonfly
```

Clone the source code of Client:

```
git clone https://github.com/dragonflyoss/client.git
cd client
```

## Operation

### Manager

#### Setup Manager

Configure
manager.yaml
, the default path is
/etc/dragonfly/manager.yaml
,
refer to
manager config
.

Set the
database.mysql.addrs
and
database.redis.addrs
address in the configuration file to your actual address.
Configuration content is as follows:

```
# Manager configuration.
database
:
type
:
mysql
mysql
:
user
:
dragonfly
-
mysql
password
:
your_mysql_password
host
:
your_mysql_host
port
:
your_mysql_port
dbname
:
manager
migrate
:
true
redis
:
addrs
:
-
dragonfly
-
redis
masterName
:
your_redis_master_name
username
:
your_redis_username
password
:
your_redis_password
db
:
0
brokerDB
:
1
backendDB
:
2
```

Run Manager:

Notice : Run Manager under dragonfly

```
# Setup Manager.
go run cmd/manager/main.go --config /etc/dragonfly/manager.yaml --console
```

#### Verify

After the Manager deployment is complete, run the following commands to verify if
Manager
is started,
and if Port
8080
and
65003
is available.

```
telnet 127.0.0.1 8080
telnet 127.0.0.1 65003
```

### Scheduler

#### Setup Scheduler

Configure
scheduler.yaml
, the default path is
/etc/dragonfly/scheduler.yaml
,
refer to
scheduler config
.

Set the
database.redis.addrs
and
manager.addr
address in the configuration file to your actual address.
Configuration content is as follows:

```
# Scheduler configuration.
database
:
redis
:
addrs
:
-
dragonfly
-
redis
masterName
:
your_redis_master_name
username
:
your_redis_username
password
:
your_redis_password
brokerDB
:
1
backendDB
:
2
manager
:
addr
:
127.0.0.1
:
65003
schedulerClusterID
:
1
keepAlive
:
interval
:
5s
```

Run Scheduler:

Notice : Run Scheduler under dragonfly

```
# Setup Scheduler.
go run cmd/scheduler/main.go --config /etc/dragonfly/scheduler.yaml --console
```

#### Verify

After the Scheduler deployment is complete, run the following commands to verify if
Scheduler
is started,
and if Port
8002
is available.

```
telnet 127.0.0.1 8002
```

### Dfdaemon

#### Setup Dfdaemon as Seed Peer

Configure
dfdaemon.yaml
, the default path is
/etc/dragonfly/dfdaemon.yaml
,
refer to
dfdaemon config
.

Set the
manager.addrs
address in the configuration file to your actual address.
Configuration content is as follows:

```
# Seed Peer configuration.
host
:
schedulerClusterID
:
1
manager
:
addr
:
http
:
//127.0.0.1
:
65003
seedPeer
:
enable
:
true
type
:
super
```

Run Dfdaemon as Seed Peer:

Notice : Run Dfdaemon under Client

```
# Setup Dfdaemon.
cargo run --bin dfdaemon -- --config /etc/dragonfly/dfdaemon.yaml -l info --console
```

#### Verify

After the Seed Peer deployment is complete, run the following commands to verify if
Seed Peer
is started,
and if Port
4000
,
4001
and
4002
is available.

```
telnet 127.0.0.1 4000
telnet 127.0.0.1 4001
telnet 127.0.0.1 4002
```

#### Setup Dfdaemon as Peer

Configure
dfdaemon.yaml
, the default path is
/etc/dragonfly/dfdaemon.yaml
,
refer to
dfdaemon config
.

Set the
manager.addrs
address in the configuration file to your actual address.
Configuration content is as follows:

```
# Peer configuration.
manager
:
addr
:
http
:
//127.0.0.1
:
65003
```

Run Dfdaemon as Peer:

Notice : Run Dfdaemon under Client

```
# Setup Dfdaemon.
cargo run --bin dfdaemon -- --config /etc/dragonfly/dfdaemon.yaml -l info --console
```

#### Verify

After the Peer deployment is complete, run the following commands to verify if
Peer
is started,
and if Port
4000
,
4001
and
4002
is available.

```
telnet 127.0.0.1 4000
telnet 127.0.0.1 4001
telnet 127.0.0.1 4002
```

---

> 完整与最新内容以官方文档为准：[Configure the Development Environment](https://d7y.io/docs/next/development-guide/configure-development-environment/)
