---
title: K8s 服务调用的底层细节分析
date: 2026-09-07 13:30:00
tags:
  - Kubernetes
  - Service
  - kube-proxy
  - DNS
categories:
  - Kubernetes
---

在 Kubernetes 集群中，服务（Service）调用的底层机制涉及多个层次的组件协作。以下从网络模型、Service 路由、DNS 解析、负载均衡等维度进行深度拆解。

---

## 一、Service 的本质与抽象

Kubernetes 中的 **Service** 是一组 Pod 的稳定访问入口。由于 Pod 是临时的（IP 会随重建而变化），Service 提供了一个固定的虚拟 IP（ClusterIP）来屏蔽后端 Pod 的变化。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: abcde
spec:
  selector:
    app: abcde
  ports:
    - protocol: TCP
      port: 80          # Service 端口
      targetPort: 8080   # Pod 容器端口
  type: ClusterIP
```

当客户端调用 `abcde` 服务时，请求经历的完整链路如下：

```
Client Pod
  │
  ├──① DNS 解析: abcde.default.svc.cluster.local → 10.96.x.x (ClusterIP)
  │
  ├──② 数据包发出: 目标 IP = 10.96.x.x, 目标端口 = 80
  │
  ├──③ kube-proxy / iptables / IPVS 拦截并 DNAT
  │     将目标地址改写为某个后端 Pod 的真实 IP（如 10.244.1.5:8080）
  │
  ├──④ CNI 网络插件负责路由（Flannel / Calico / Cilium 等）
  │
  └──⑤ 数据包到达目标 Pod
```

---

## 二、DNS 解析的底层细节

### 2.1 CoreDNS

集群内 DNS 由 **CoreDNS** 提供（以 Deployment 形式运行）。当 Pod 中的应用发起 `abcde` 的 DNS 查询时：

1. Pod 的 `/etc/resolv.conf` 指向 CoreDNS 的 ClusterIP（如 `10.96.0.10`）
2. CoreDNS 收到查询后，根据请求的域名匹配规则：
   - `abcde` → 补全为 `abcde.<namespace>.svc.cluster.local`
   - 查询 `endpoints` 资源（即后端 Pod IP 列表）
3. 返回 ClusterIP（默认行为）或通过 **Headless Service** 直接返回 Pod IP 列表

### 2.2 DNS 策略（dnsPolicy）

Pod 的 DNS 策略影响解析行为：

| 策略 | 说明 |
|---|---|
| `ClusterFirst`（默认） | 集群域名走 CoreDNS，外部域名走上游 DNS |
| `Default` | 继承节点的 `/etc/resolv.conf` |
| `ClusterFirstWithHostNet` | hostNetwork Pod 仍优先走 CoreDNS |
| `None` | 完全自定义 `dnsConfig` |

---

## 三、kube-proxy 的工作模式

`kube-proxy` 是运行在每个节点上的组件，负责将 Service 的 ClusterIP 映射到后端 Pod。它有三种工作模式：

### 3.1 iptables 模式（默认）

```bash
# 查看 iptables 规则
iptables -t nat -L KUBE-SERVICES -n
```

工作原理：
- kube-proxy 监听 API Server 中 Service 和 Endpoints 的变化
- 在 `nat` 表中创建规则链（如 `KUBE-SVC-XXXX`, `KUBE-SEP-XXXX`）
- 当数据包命中 ClusterIP 时，通过 **DNAT** 将目标地址改写为某个后端 Pod IP
- 使用 **概率匹配** 实现简单的负载均衡（如两个 Pod 各 50%）

```
Chain KUBE-SVC-XXX (1 references)
target     prot opt source     destination
KUBE-SEP-AAA  all  --  0.0.0.0/0  0.0.0.0/0  statistic mode random probability 0.50000000000
KUBE-SEP-BBB  all  --  0.0.0.0/0  0.0.0.0/0
```

**缺点**：当后端 Pod 数量很大时（数千个），iptables 规则线性增长，更新和匹配性能下降。

### 3.2 IPVS 模式

```bash
# 查看 IPVS 规则
ipvsadm -Ln
```

- 基于内核态的 **IP Virtual Server**，性能远优于 iptables
- 支持多种负载均衡算法：`rr`（轮询）、`lc`（最少连接）、`sh`（源地址哈希）、`dh`（目标地址哈希）等
- 规则查找使用哈希表，时间复杂度 O(1)，适合大规模集群

### 3.3 nftables 模式（Kubernetes 1.29+）

- 基于 Linux nftables 子系统替代 iptables
- 语法更简洁，性能更优，是未来的演进方向

---

## 四、Service 类型与调用差异

| 类型 | ClusterIP | NodePort | LoadBalancer | ExternalName |
|---|---|---|---|---|
| 集群内可访问 | 是 | 是 | 是 | DNS CNAME |
| 集群外可访问 | 否 | 是（节点IP:NodePort） | 是（LB IP） | 是（外部域名） |
| 底层机制 | DNAT | DNAT + 节点端口监听 | 云 LB + NodePort | DNS 重写 |

---

## 五、Pod 到 Pod 通信的底层：CNI

Service 的 DNAT 之后，数据包需要通过 **CNI（Container Network Interface）** 网络插件送达目标 Pod。常见实现：

### 5.1 Flannel（VXLAN 模式）
- 跨节点通信时，原始数据包被封装在 VXLAN 报文中
- `flanneld` 维护子网与节点的映射关系
- 封装开销约 50 字节

### 5.2 Calico
- 默认使用 **BGP** 协议在节点间交换路由信息
- 每个 Pod 的 IP 路由直接写入节点路由表
- 支持 **NetworkPolicy** 实现网络策略

### 5.3 eBPF 方案（Cilium）
- 绕过 kube-proxy，直接在内核态完成 Service 的负载均衡
- 使用 eBPF 程序 hook 在 socket 层或 XDP 层
- 性能最优，功能最强（支持 L7 策略、透明加密等）

```
# Cilium 的 eBPF 路径（绕过 iptables/IPVS）
Client → socket connect() → eBPF cgroup/connect4 → 直接选择后端 Pod IP → 路由送达
```

---

## 六、连接跟踪（conntrack）

无论 iptables 还是 IPVS 模式，DNAT 都依赖内核的 **conntrack** 模块：

```bash
# 查看连接跟踪表
conntrack -L -p tcp --dport 80
```

- 首包经过 DNAT 规则匹配后，创建 conntrack 条目
- 后续包直接匹配已有条目，跳过规则匹配（状态跟踪）
- conntrack 表满时会导致丢包：`nf_conntrack: table full, dropping packet`

调优建议：
```bash
# 增大 conntrack 表大小
sysctl -w net.netfilter.nf_conntrack_max=262144
```

---

## 七、服务调用的完整数据包旅程（总结）

```
[Client Pod 内应用]
    │
    │ ① getaddrinfo("abcde") → CoreDNS → 返回 ClusterIP
    │
    │ ② send() 目标=ClusterIP:80
    │
    │ ③ 数据包从 eth0 (veth pair) 发出
    │
    │ ④ 到达节点的根命名空间（root ns）
    │
    │ ⑤ iptables/IPVS 匹配 → DNAT → 目标改为 Pod_IP:8080
    │      conntrack 记录映射关系
    │
    │ ⑥ 路由查找：
    │    - 同节点 Pod：直接通过 veth pair 送达
    │    - 跨节点 Pod：通过 CNI 封装/路由转发
    │
    │ ⑦ 数据包到达目标 Pod 的 network namespace
    │
    │ ⑧ 容器内进程收到请求并响应
    │
    │ ⑨ 响应包原路返回（SNAT 确保对称路径）
    │
    ▼
[Client Pod 收到响应]
```

---

## 八、常见问题排查清单

```bash
# 1. 检查 Service 是否有 Endpoints
kubectl get svc abcde -o wide
kubectl get endpoints abcde

# 2. 检查 CoreDNS 是否正常
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system logs -l k8s-app=kube-dns

# 3. 从 Pod 内测试 DNS 和连通性
kubectl exec -it debug-pod -- nslookup abcde
kubectl exec -it debug-pod -- curl -v http://abcde:80

# 4. 检查 iptables 规则是否正确生成
iptables -t nat -L KUBE-SERVICES | grep abcde

# 5. 检查 conntrack
conntrack -L -p tcp --dport 8080

# 6. 检查 kube-proxy 日志
kubectl -n kube-system logs -l k8s-app=kube-proxy
```

---

如果 `abcde` 是你们具体的业务服务名称，可以进一步提供该服务的 YAML 配置、网络插件类型和具体故障现象，我可以给出更有针对性的排查方案。
