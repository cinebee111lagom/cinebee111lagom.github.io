---
title: etcd v3.7 抓取：Install
date: 2026-09-13 09:02:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/install/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/install/>

---

## Requirements

Before installing etcd, see the following pages:

Supported platforms

Hardware recommendations

## Install pre-built binaries

The easiest way to install etcd is from pre-built binaries:

Download the compressed archive file for your platform from
Releases
,
choosing release
v3.7.0
or later.

Unpack the archive file. This results in a directory containing the binaries.

Add the executable binaries to your path. For example, rename and/or move
the binaries to a directory in your path (like
/usr/local/bin
), or add the
directory created by the previous step to your path.

/usr/local/bin

From a shell, test that
etcd
is in your path:
$ etcd --version
etcd Version: 3.7.0
...

From a shell, test that
etcd
is in your path:

etcd

```
$ etcd --version
etcd Version: 3.7.0
...
```

## Build from source

If you have
Go version 1.21+
, you can build etcd from
source by following these steps:

Download the etcd repo as a zip file
and unzip it, or clone the
repo using the following command.
$ git clone -b v3.7.0 https://github.com/etcd-io/etcd.git
To build from
main@HEAD
, omit the
-b v3.7.0
flag.

Download the etcd repo as a zip file
and unzip it, or clone the
repo using the following command.

```
$ git clone -b v3.7.0 https://github.com/etcd-io/etcd.git
```

To build from
main@HEAD
, omit the
-b v3.7.0
flag.

main@HEAD

-b v3.7.0

Change directory:
$
cd
etcd

Change directory:

```
$
cd
etcd
```

Run the build script:
$ ./scripts/build.sh
The binaries are under the
bin
directory.

Run the build script:

```
$ ./scripts/build.sh
```

The binaries are under the
bin
directory.

bin

Add the full path to the
bin
directory to your path, for example:
$
export
PATH
=
"
$PATH
:`pwd`/bin"

Add the full path to the
bin
directory to your path, for example:

bin

```
$
export
PATH
=
"
$PATH
:`pwd`/bin"
```

Test that
etcd
is in your path:
$ etcd --version

Test that
etcd
is in your path:

etcd

```
$ etcd --version
```

## Installation via OS packages

Disclaimer: etcd installations through OS package managers can deliver outdated versions since they are not being automatically maintained nor officially supported by etcd project. Therefore use OS packages with caution.

There are various ways of installing etcd on different operating systems and these are just some examples how it can be done.

### MacOS (Homebrew)

Update homebrew:

```
$ brew update
```

Install etcd:

```
$ brew install etcd
```

Verify install

```
$ etcd --version
```

## Linux

Although installing etcd through many major Linux distributions’ official repositories and package managers is possible, the published versions can be significantly outdated. So, installing this way is strongly discouraged.

The recommended way to install etcd on Linux is either through
pre-built binaries
or by using Homebrew.

### Homebrew on Linux

Homebrew can run on Linux
, and can provide recent software versions.

Prerequisites
Update Homebrew:
$ brew update

Prerequisites

Update Homebrew:
$ brew update

Update Homebrew:

```
$ brew update
```

Procedure
Install using
brew
:
$ brew install etcd

Procedure

Install using
brew
:
$ brew install etcd

Install using
brew
:

brew

```
$ brew install etcd
```

Result
Verify installation by getting the version:
$ etcd --version
etcd Version: 3.7.0
...

Result

Verify installation by getting the version:
$ etcd --version
etcd Version: 3.7.0
...

Verify installation by getting the version:

```
$ etcd --version
etcd Version: 3.7.0
...
```

## Docker

etcd uses
gcr.io/etcd-development/etcd
as a
primary container registry, and
quay.io/coreos/etcd
as
secondary.

gcr.io/etcd-development/etcd

quay.io/coreos/etcd

To run etcd using Docker:

```
ETCD_VER
=
v3.7.0
rm -rf /tmp/etcd-data.tmp
&&
mkdir -p /tmp/etcd-data.tmp
&&
\
docker rmi gcr.io/etcd-development/etcd:
${
ETCD_VER
}
||
true
&&
\
docker run
\
-p 2379:2379
\
-p 2380:2380
\
--mount
type
=
bind,source
=
/tmp/etcd-data.tmp,destination
=
/etcd-data
\
--name etcd-gcr-
${
ETCD_VER
}
\
gcr.io/etcd-development/etcd:
${
ETCD_VER
}
\
/usr/local/bin/etcd
\
--name s1
\
--data-dir /etcd-data
\
--listen-client-urls http://0.0.0.0:2379
\
--advertise-client-urls http://0.0.0.0:2379
\
--listen-peer-urls http://0.0.0.0:2380
\
--initial-advertise-peer-urls http://0.0.0.0:2380
\
--initial-cluster
s1
=
http://0.0.0.0:2380
\
--initial-cluster-token tkn
\
--initial-cluster-state new
\
--log-level info
\
--logger zap
\
--log-outputs stderr
docker
exec
etcd-gcr-
${
ETCD_VER
}
/usr/local/bin/etcd --version
docker
exec
etcd-gcr-
${
ETCD_VER
}
/usr/local/bin/etcdctl version
docker
exec
etcd-gcr-
${
ETCD_VER
}
/usr/local/bin/etcdutl version
docker
exec
etcd-gcr-
${
ETCD_VER
}
/usr/local/bin/etcdctl endpoint health
docker
exec
etcd-gcr-
${
ETCD_VER
}
/usr/local/bin/etcdctl put foo bar
docker
exec
etcd-gcr-
${
ETCD_VER
}
/usr/local/bin/etcdctl get foo
```

## Installation as part of Kubernetes installation

Running etcd as a Kubernetes StatefulSet

## Installation check

For a slightly more involved sanity check of your installation, see
Quickstart
.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Install](https://etcd.io/docs/v3.7/install/)
