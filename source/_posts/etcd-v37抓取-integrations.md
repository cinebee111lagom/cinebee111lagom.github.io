---
title: etcd v3.7 抓取：Libraries and tools
date: 2026-09-13 09:06:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/integrations/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/integrations/>

---

Note that third-party libraries and tools (not hosted on
https://github.com/etcd-io
) mentioned below are not tested or maintained by the etcd team. Before using them, users are recommended to read and investigate them.

## Tools

etcdctl
- A command line client for etcd

etcd-dump
- Command line utility for dumping/restoring etcd.

etcd-fs
- FUSE filesystem for etcd

etcddir
- Realtime sync etcd and local directory. Work with windows and linux.

etcd-browser
- A web-based key/value editor for etcd using AngularJS

etcd-lock
- Master election & distributed r/w lock implementation using etcd - Supports v2

etcd-console
- A web-base key/value editor for etcd using PHP

etcd-viewer
- An etcd key-value store editor/viewer written in Java

etcdtool
- Export/Import/Edit etcd directory as JSON/YAML/TOML and Validate directory using JSON schema

etcdloadtest
- A command line load test client for etcd version 3.0 and above.

etcd-tui
- A modern terminal user interface (TUI) for interacting with your etcd database. Navigate keys, view values, filter data, and manage your etcd cluster directly from your terminal.

etcdfinder
- A lightning-fast, modern web UI for etcd with instant search. Supports both etcd v2 and v3.

lucas
- A web-based key-value viewer for kubernetes etcd3.0+ cluster.

etcd-manager
- A modern, efficient, multi-platform and free etcd 3.x GUI & client tool. Available for Windows, Linux and Mac.

etcd-backup-restore
- Utility to periodically and incrementally backup and restore the etcd.

etcd-druid
- A Kubernetes operator to deploy etcd clusters and manage day-2 operations.

etcdadm
- A command-line tool for operating an etcd cluster.

etcd-defrag
- An easier to use and smarter etcd defragmentation tool.

etcdhelper
- An intellij platform plugin for etcd.

## Libraries

The sections below list etcd client libraries by language.

### Go

etcd/client/v3
- the officially maintained Go client for v3

go-etcd
- the deprecated official client. May be useful for older (<2.0.0) versions of etcd.

encWrapper
- encWrapper is an encryption wrapper for the etcd client Keys API/KV.

### Java

coreos/jetcd
- Supports v3

justinsb/jetcd

cdancy/etcd-rest
- Uses jclouds to provide a complete implementation of v2 API.

IBM/etcd-java

### Scala

maciej/etcd-client
- Supports v2. Akka HTTP-based fully async client

eiipii/etcdhttpclient
- Supports v2. Async HTTP client based on Netty and Scala Futures.

mingchuno/etcd4s
- Supports v3 using gRPC with optional Akka Stream support.

### Perl

hexfusion/perl-net-etcd
- Supports v3 grpc gateway HTTP API

robn/p5-etcd
- Supports v2

### Python

kragniz/python-etcd3
- Client for v3

jplana/python-etcd
- Supports v2

russellhaering/txetcd
- a Twisted Python library

cholcombe973/autodock
- A docker deployment automation tool

lisael/aioetcd
- (Python 3.4+) Asyncio coroutines client (Supports v2)

txaio-etcd
- Asynchronous etcd v3-only client library for Twisted (today) and asyncio (future)

dims/etcd3-gateway
- etcd v3 API library using the HTTP grpc gateway

aioetcd3
- (Python 3.6+) etcd v3 API for asyncio

Revolution1/etcd3-py
- (python2.7 and python3.5+) Python client for etcd v3, using gRPC-JSON-Gateway

### Node

mixer/etcd3
- Supports v3

stianeikeland/node-etcd
- Supports v2 (w Coffeescript)

lavagetto/nodejs-etcd
- Supports v2

deedubs/node-etcd-config
- Supports v2

### Ruby

iconara/etcd-rb

jpfuentes2/etcd-ruby

ranjib/etcd-ruby
- Supports v2

davissp14/etcdv3-ruby
- Supports v3

apache/celix/etcdlib
- Supports v2

jdarcy/etcd-api
- Supports v2

shafreeck/cetcd
- Supports v2

### C++

edwardcapriolo/etcdcpp
- Supports v2

suryanathan/etcdcpp
- Supports v2 (with waits)

nokia/etcd-cpp-api
- Supports v2

etcd-cpp-apiv3/etcd-cpp-apiv3
- Supports v3

### Clojure

aterreno/etcd-clojure

dwwoelfel/cetcd
- Supports v2

rthomas/clj-etcd
- Supports v2

### Erlang

marshall-lee/etcd.erl
- Supports v2

zhongwencool/eetcd
- Supports v3+ (GRPC only)

### Elixir

team-telnyx/etcdex
- Supports v3+ (GRPC only)

### .NET

wangjia184/etcdnet
- Supports v2

drusellers/etcetera

shubhamranjan/dotnet-etcd
- Supports v3+ (GRPC only)

SimplifyNet/Etcd.Microsoft.Extensions.Configuration

### PHP

linkorb/etcd-php

activecollab/etcd

ouqiang/etcd-php
- Client for v3 gRPC gateway

### Haskell

wereHamster/etcd-hs

ropensci/etseed

### Nim

etcd_client

### Tcl

efrecon/etcd-tcl
- Supports v2, except wait.

### Rust

jimmycuadra/rust-etcd
- Supports v2

### Gradle

gradle-etcd-rest-plugin
- Supports v2

### Lua

api7/lua-resty-etcd
- Supports v2 and v3 (grpc gateway HTTP API)

## Deployment tools

### Chef integrations

coderanger/etcd-chef

### Chef cookbooks

spheromak/etcd-cookbook

### BOSH releases

cloudfoundry-community/etcd-boshrelease

cloudfoundry/cf-release

## Projects using etcd

etcd Raft users
- projects using etcd’s raft library implementation.

apache/apisix
- A dynamic, real-time, high-performance API gateway

apache/celix
- an implementation of the OSGi specification adapted to C and C++

binocarlos/yoda
- etcd + ZeroMQ

blox/blox
- a collection of open source projects for container management and orchestration with AWS ECS

calavera/active-proxy
- HTTP Proxy configured with etcd

chain/chain
- software designed to operate and connect to highly scalable permissioned blockchain networks

derekchiang/etcdplus
- A set of distributed synchronization primitives built upon etcd

go-discover
- service discovery in Go

gleicon/goreman
- Branch of the Go Foreman clone with etcd support

garethr/hiera-etcd
- Puppet hiera backend using etcd

mattn/etcd-vim
- SET and GET keys from inside vim

mattn/etcdenv
- “env” shebang with etcd integration

kelseyhightower/confd
- Manage local app config files using templates and data from etcd

configdb
- A REST relational abstraction on top of arbitrary database backends, aimed at storing configs and inventories.

kubernetes/kubernetes
- Container cluster manager introduced by Google.

mailgun/vulcand
- HTTP proxy that uses etcd as a configuration backend.

duedil-ltd/discodns
- Simple DNS nameserver using etcd as a database for names and records.

skynetservices/skydns
- RFC compliant DNS server

xordataexchange/crypt
- Securely store values in etcd using GPG encryption

spf13/viper
- Go configuration library, reads values from ENV, pflags, files, and etcd with optional encryption

lytics/metafora
- Go distributed task library

ryandoyle/nss-etcd
- A GNU libc NSS module for resolving names from etcd.

Gru
- Orchestration made easy with Go

Vitess
- Vitess is a database clustering system for horizontal scaling of MySQL.

lclarkmichalek/etcdhcp
- DHCP server that uses etcd for persistence and coordination.

openstack/networking-vpp
- A networking driver that programs the
FD.io VPP dataplane
to provide
OpenStack
cloud virtual networking

OpenStack
- OpenStack services can rely on etcd as a base service.

CoreDNS
- CoreDNS is a DNS server that chains plugins, part of CNCF and Kubernetes

Uber M3
- M3: Uber’s Open Source, Large-scale Metrics Platform for Prometheus

Rook
- Storage Orchestration for Kubernetes

Patroni
- A template for PostgreSQL High Availability with ZooKeeper, etcd, or Consul

Trillian
- Trillian implements a Merkle tree whose contents are served from a data storage layer, to allow scalability to extremely large trees.

Apache APISIX
- Apache APISIX is a dynamic, real-time, high-performance API gateway.

purpleidea/mgmt
- Next generation distributed, event-driven, parallel config management!

Portworx/kvdb
- The internal kvdb for storing Portworx cluster configuration.

Apache Pulsar
- Apache Pulsar is an open-source, distributed messaging and streaming platform built for the cloud.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Libraries and tools](https://etcd.io/docs/v3.7/integrations/)
