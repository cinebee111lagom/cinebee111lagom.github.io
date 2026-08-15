---
title: Volcano 抓取：Volcano Job 插件 -- SSH 用户指南
date: 2026-09-14 09:49:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_ssh_plugin>

---

## 背景

SSH 插件
用于实现 Volcano Job 内 Pod 之间的免密 SSH 登录，这在
MPI
等分布式工作负载中是必需的。通常与
svc
插件配合使用。

## 要点

若配置了
ssh-key-file-path
，请确保目标目录下已存在私钥与公钥。多数场景建议保留默认值。

若配置了
ssh-private-key
或
ssh-public-key
，请确保取值正确。多数场景建议保留默认密钥。

配置 SSH 插件后，会创建名为
{job-name}-ssh
的 Secret，其中包含
authorized_keys
、
id_rsa
、
config
与
id_rsa.pub
，并以 Volume 形式挂载到 Job 内所有容器（含 initContainers）的指定路径。

默认可在
/root/.ssh/config
中查看 Job 内所有主机名；该文件包含主机名与子域名的对应关系。

配置 SSH 插件后，可在同一 Job 内通过
ssh hostname
免密登录其他 Pod。

## 参数说明

## 说明

DEFAULT_PRIVATE_KEY
与
DEFAULT_PUBLIC_KEY
因内容过长未在表中完整列出，请参阅下方示例。

Volcano 不负责校验
ssh-key-file-path
，请自行确保路径正确。

多数场景建议留空并使用默认值；此时 Volcano 会自动生成密钥对并完成相关配置。

## 示例

```
apiVersion
:
batch.volcano.sh/v1alpha1
kind
:
Job
metadata
:
name
:
mpi
-
job
spec
:
minAvailable
:
3
schedulerName
:
volcano
plugins
:
ssh
:
[
]
## 注册 SSH 插件
svc
:
[
]
tasks
:
-
replicas
:
1
name
:
mpimaster
template
:
spec
:
containers
:
-
command
:
-
/bin/bash
-
-
c
-
|
mkdir -p /var/run/sshd; /usr/sbin/sshd;
MPI_HOST=`cat /etc/volcano/mpiworker.host | tr "\n" ","`;
sleep 10;
mpiexec --allow-run-as-root --host ${MPI_HOST} -np 2 --prefix /usr/local/openmpi-3.1.5 python /tmp/gpu-test.py;
sleep 3600;
image
:
lyd911/mindspore
-
gpu
-
example
:
0.2.0
name
:
mpimaster
ports
:
-
containerPort
:
22
name
:
mpijob
-
port
workingDir
:
/home
restartPolicy
:
OnFailure
-
replicas
:
2
name
:
mpiworker
template
:
spec
:
containers
:
-
command
:
-
/bin/bash
-
-
c
-
|
mkdir -p /var/run/sshd; /usr/sbin/sshd -D;
image
:
lyd911/mindspore
-
gpu
-
example
:
0.2.0
name
:
mpiworker
resources
:
limits
:
nvidia.com/gpu
:
"1"
ports
:
-
containerPort
:
22
name
:
mpijob
-
port
workingDir
:
/home
restartPolicy
:
OnFailure
```

## 说明

本示例将创建一个包含 1 个
master
与 2 个
worker
的 MPI Job。

因启用了
svc
插件，可在任意 Pod 中通过环境变量获取所有主机；若使用默认 SSH 配置，也可在
/root/.ssh/config
中查看主机列表。

```
[root@mpi-job-master-0 /]# cat /root/.ssh/config
StrictHostKeyChecking no
UserKnownHostsFile /dev/null
Host mpi-job-mpimaster-0
HostName mpi-job-mpimaster-0.mpi-job
Host mpi-job-mpiworker-0
HostName mpi-job-mpiworker-0.mpi-job
Host mpi-job-mpiworker-1
HostName mpi-job-mpiworker-1.mpi-job
```

可在
master
Pod 中按如下方式登录其他主机：

```
[root@mpi-job-master-0 /]# ssh mpi-job-mpiworker-0
Warning: Permanently added 'mpi-job-mpiworker-0.mpi-job,X.X.X.X' (ECDSA) to the list of known hosts.
Welcome to Ubuntu 18.04.3 LTS (GNU/Linux 3.10.0-1160.36.2.el7.x86_64 x86_64)
* Documentation:  https://help.ubuntu.com
* Management:     https://landscape.canonical.com
* Support:        https://ubuntu.com/advantage
This system has been minimized by removing packages and content that are
not required on a system that users do not log into.
To restore this content, you can run the 'unminimize' command.
Last login: Thu Apr 14 07:19:05 2022 from 10.244.0.67
root@mpi-job-mpiworker-0:~#
```

## 说明

请确保所有容器内均已提供
sshd
服务。

---

> 完整与最新内容以官方文档为准：[Volcano Job 插件 -- SSH 用户指南](https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_ssh_plugin)
