---
title: etcd v3.7 抓取：Authentication
date: 2026-09-13 09:27:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/op-guide/authentication/authentication/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/op-guide/authentication/authentication/>

---

auth
,
user
,
role
for authentication:

auth

user

role

```
export
ETCDCTL_API
=
3
ENDPOINTS
=
localhost:2379
etcdctl --endpoints
=
${
ENDPOINTS
}
role add root
etcdctl --endpoints
=
${
ENDPOINTS
}
role get root
etcdctl --endpoints
=
${
ENDPOINTS
}
user add root
etcdctl --endpoints
=
${
ENDPOINTS
}
user grant-role root root
etcdctl --endpoints
=
${
ENDPOINTS
}
user get root
etcdctl --endpoints
=
${
ENDPOINTS
}
role add role0
etcdctl --endpoints
=
${
ENDPOINTS
}
role grant-permission role0 readwrite foo
etcdctl --endpoints
=
${
ENDPOINTS
}
user add user0
etcdctl --endpoints
=
${
ENDPOINTS
}
user grant-role user0 role0
etcdctl --endpoints
=
${
ENDPOINTS
}
auth
enable
# now all client requests go through auth
etcdctl --endpoints
=
${
ENDPOINTS
}
--user
=
user0:123 put foo bar
etcdctl --endpoints
=
${
ENDPOINTS
}
get foo
# permission denied, user name is empty because the request does not issue an authentication request
etcdctl --endpoints
=
${
ENDPOINTS
}
--user
=
user0:123 get foo
# user0 can read the key foo
etcdctl --endpoints
=
${
ENDPOINTS
}
--user
=
user0:123 get foo1
```

### Note:

This is just a stub which needs to be filled and updated with more information on authentication. The text above is just a code example.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Authentication](https://etcd.io/docs/v3.7/op-guide/authentication/authentication/)
