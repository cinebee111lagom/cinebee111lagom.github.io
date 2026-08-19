---
title: 团队Kubeconfig分发策略与最佳实践
date: 2026-09-08 10:45:00
tags:
  - Kubernetes
  - kubeconfig
  - RBAC
  - 安全
categories:
  - Kubernetes
---

## 核心问题

直接复制 `~/.kube/config` 给所有人？**绝对不行。** 每个人应该拿到**最小权限**的凭证，且凭证可撤销、可审计、可轮转。

---

## 策略一：按用户签发独立客户端证书

### 1.1 用 CA 为每个成员签发证书

```bash
#!/bin/bash
# gen-user-cert.sh
# 用法: ./gen-user-cert.sh <username> <group> <days>

USERNAME=$1
GROUP=${2:-developers}
DAYS=${3:-365}
CA_DIR="/etc/kubernetes/pki"
OUT_DIR="/opt/kube-certs/${USERNAME}"

mkdir -p "$OUT_DIR"

# 生成私钥
openssl genrsa -out "${OUT_DIR}/${USERNAME}.key" 2048

# 生成 CSR（CN=username, O=group）
openssl req -new \
  -key "${OUT_DIR}/${USERNAME}.key" \
  -out "${OUT_DIR}/${USERNAME}.csr" \
  -subj "/CN=${USERNAME}/O=${GROUP}"

# 用 K8s CA 签发证书
openssl x509 -req \
  -in "${OUT_DIR}/${USERNAME}.csr" \
  -CA "${CA_DIR}/ca.crt" \
  -CAkey "${CA_DIR}/ca.key" \
  -CAcreateserial \
  -out "${OUT_DIR}/${USERNAME}.crt" \
  -days "${DAYS}"

echo "证书已签发: ${OUT_DIR}/"
```

### 1.2 为每个用户生成专属 kubeconfig

```bash
#!/bin/bash
# gen-user-kubeconfig.sh
# 用法: ./gen-user-kubeconfig.sh <username> <apiserver>

USERNAME=$1
APISERVER=${2:-"https://10.0.0.1:6443"}
CA_DIR="/etc/kubernetes/pki"
CERT_DIR="/opt/kube-certs/${USERNAME}"
KUBECONFIG_OUT="/opt/kube-configs/${USERNAME}-kubeconfig.yaml"

mkdir -p "$(dirname "$KUBECONFIG_OUT")"

# base64 编码
CA_DATA=$(base64 -w0 "${CA_DIR}/ca.crt")
CERT_DATA=$(base64 -w0 "${CERT_DIR}/${USERNAME}.crt")
KEY_DATA=$(base64 -w0 "${CERT_DIR}/${USERNAME}.key")

cat > "$KUBECONFIG_OUT" <<EOF
apiVersion: v1
kind: Config
current-context: default
clusters:
- name: kubernetes
  cluster:
    server: ${APISERVER}
    certificate-authority-data: ${CA_DATA}
users:
- name: ${USERNAME}
  user:
    client-certificate-data: ${CERT_DATA}
    client-key-data: ${KEY_DATA}
contexts:
- name: default
  context:
    cluster: kubernetes
    user: ${USERNAME}
    namespace: ${USERNAME}    # 默认命名空间隔离
EOF

echo "kubeconfig 已生成: ${KUBECONFIG_OUT}"
```

**但这种方法的缺陷很明显：**
- 证书无法吊销（K8s 原生不支持 CRL）
- 证书签发后无法限制有效期缩短
- 无法与企业 SSO 集成

---

## 策略二：基于 ServiceAccount + Token（适合机器/CI）

```bash
# 1. 创建 ServiceAccount
kubectl create serviceaccount ci-deployer -n production

# 2. 绑定 RBAC
kubectl create rolebinding ci-deployer-binding \
  --role=deployment-manager \
  --serviceaccount=production:ci-deployer \
  -n production

# 3. 获取 Token（K8s 1.24+ 需要手动创建 Token Secret）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: ci-deployer-token
  namespace: production
  annotations:
    kubernetes.io/service-account.name: ci-deployer
type: kubernetes.io/service-account-token
EOF

# 4. 提取凭证
TOKEN=$(kubectl get secret ci-deployer-token -n production \
  -o jsonpath='{.data.token}' | base64 -d)
CA=$(kubectl get secret ci-deployer-token -n production \
  -o jsonpath='{.data.ca\.crt}')
```

**适用场景：** CI/CD pipeline、脚本、机器人账号
**不适用：** 开发人员日常操作（无审计追踪、Token 难以自动轮转）

---

## 策略三：OIDC 集成（推荐的生产方案）

这是**企业级最佳实践**——不直接分发 kubeconfig 中的凭证，而是对接企业身份系统。

### 架构

```
开发人员                OIDC Provider              API Server
   │                      (Dex/Okta/                │
   │                       Azure AD)                │
   │                          │                     │
   │  1. kubectl get pods     │                     │
   │  ──→ 触发 exec 插件 ──→  │                     │
   │                          │                     │
   │  2. 浏览器弹出登录页  ←── │                     │
   │     用户输入密码/SAML ──→ │                     │
   │                          │                     │
   │  3. 返回 id_token   ←────│                     │
   │                          │                     │
   │  4. 带 Bearer Token ──────────────────────────→ │
   │                          │                     │
   │  5. API Server 验证 Token → OIDC Provider      │
   │                          │                     │
   │  6. 映射 claims 为 user/group                  │
   │     执行 RBAC 检查                             │
   │  ←───────────────────────────────────────── 返回结果
```

### 3.1 配置 API Server 启用 OIDC

```yaml
# /etc/kubernetes/manifests/kube-apiserver.yaml
spec:
  containers:
  - command:
    - kube-apiserver
    - --oidc-issuer-url=https://dex.example.com
    - --oidc-client-id=kubernetes
    - --oidc-username-claim=email
    - --oidc-groups-claim=groups
    - --oidc-ca-file=/etc/kubernetes/pki/oidc-ca.crt
    # 可选：前缀，避免与其它认证方式冲突
    - --oidc-username-prefix=oidc:
    - --oidc-groups-prefix=oidc:
```

### 3.2 为团队分发的 kubeconfig 模板

```yaml
# kubeconfig-oidc-template.yaml
# 每个人拿到的都是这份，无需包含任何私钥/密码
apiVersion: v1
kind: Config
preferences: {}
current-context: prod-cluster

clusters:
- name: prod-cluster
  cluster:
    server: https://k8s-api.example.com:6443
    certificate-authority-data: <CA_BASE64>

users:
- name: oidc-user
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1
      kind: ExecCredential
      command: kubectl
      args:
      - oidc-login
      - get-token
      - --oidc-issuer-url=https://dex.example.com
      - --oidc-client-id=kubernetes
      - --oidc-client-secret=<CLIENT_SECRET>    # 注意：这个 secret 只能做登录，不能操作集群
      - --oidc-extra-scope="openid profile email groups offline_access"
      - --grant-type=authcode
      installHint: |
        请安装 kubelogin：
        brew install int128/kubelogin/kubelogin
        或 https://github.com/int128/kubelogin

contexts:
- name: prod-cluster
  context:
    cluster: prod-cluster
    user: oidc-user
    namespace: default
```

### 3.3 RBAC 绑定（按 OIDC 组映射）

```yaml
# 开发团队只能操作 dev 命名空间
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-team-binding
  namespace: development
subjects:
- kind: Group
  name: oidc:dev-team        # OIDC token 中的 groups claim
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: edit                  # 内置角色：可读写大部分资源，不能改 RBAC
  apiGroup: rbac.authorization.k8s.io

---
# SRE 团队可以操作所有命名空间
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: sre-team-binding
subjects:
- kind: Group
  name: oidc:sre-team
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: admin
  apiGroup: rbac.authorization.k8s.io
```

---

## 策略四：借助 kubexec / Teleport / Rancher 等平台

```
┌─────────────────────────────────────────────────────────┐
│  方案          │ Token 管理 │ SSO 集成 │ 审计  │ 运维成本 │
├────────────────┼────────────┼──────────┼───────┼─────────┤
│ 手动证书签发   │ 无（永久）  │ 无       │ 弱    │ 高      │
│ ServiceAccount │ 手动轮转   │ 无       │ 中    │ 中      │
│ OIDC + Dex     │ 自动刷新   │ 强       │ 强    │ 中      │
│ Teleport       │ 自动       │ 强       │ 极强  │ 高      │
│ Rancher        │ 自动       │ 强       │ 强    │ 中      │
│ AWS EKS + IAM  │ 自动       │ AWS SSO  │ CloudTrail │ 低 │
│ GKE + IAM      │ 自动       │ GCP IAM  │ Cloud Audit  │ 低 │
└─────────────────────────────────────────────────────────┘
```

---

## 实际分发流程建议

### 分发前的 RBAC 设计

```yaml
# 定义三个层级的 ClusterRole

# 1. 只读（新人/观察者）
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: viewer-custom
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "events"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]

---
# 2. 开发者（可在指定命名空间读写）
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: developer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "services", "deployments", "configmaps",
              "secrets", "jobs", "cronjobs", "ingresses"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods/log", "pods/exec"]
  verbs: ["get", "create"]

---
# 3. SRE（集群管理权限）
# 直接使用内置 admin ClusterRole，或自定义更精细的角色
```

### 分发脚本（自动化）

```bash
#!/bin/bash
# distribute-kubeconfig.sh
# 用法: ./distribute-kubeconfig.sh <team-list.csv>
# CSV 格式: username,email,role,namespace

TEAM_FILE=$1
KUBECONFIG_TEMPLATE="kubeconfig-oidc-template.yaml"
OUTPUT_DIR="/opt/team-kubeconfigs"

while IFS=',' read -r username email role namespace; do
  echo "=== 为 ${username} 生成 kubeconfig ==="
  
  # 1. 在 OIDC Provider (如 Dex) 中创建用户映射
  # 2. 在 K8s 中创建 RBAC 绑定
  kubectl create rolebinding "${username}-${role}-binding" \
    --clusterrole="${role}" \
    --user="oidc:${email}" \
    --namespace="${namespace}" \
    --dry-run=client -o yaml | kubectl apply -f -
  
  # 3. 生成个人 kubeconfig
  sed "s|<USER_EMAIL>|${email}|g" \
      "$KUBECONFIG_TEMPLATE" > "${OUTPUT_DIR}/${username}-kubeconfig.yaml"
  
  # 4. 通过安全渠道分发（不走明文邮件！）
  #    选项 A: 上传到 Vault，用户自助获取
  #    vault kv put secret/kubeconfig/${username} \
  #      config=@"${OUTPUT_DIR}/${username}-kubeconfig.yaml"
  
  #    选项 B: 加密后通过公司内部工具发送
  #    gpg --encrypt --recipient "${email}" \
  #      "${OUTPUT_DIR}/${username}-kubeconfig.yaml"
  
  echo "✓ ${username} 的 kubeconfig 已生成"
done < "$TEAM_FILE"
```

---

## 安全分发的黄金规则

```
┌──────────────────────────────────────────────────┐
│                                                  │
│   ✗ 不要通过 Slack/邮件/微信 发送 kubeconfig     │
│   ✗ 不要把 kubeconfig 提交到 Git 仓库            │
│   ✗ 不要给所有人 cluster-admin                    │
│   ✗ 不要在 kubeconfig 中硬编码长期有效的 token    │
│                                                  │
│   ✓ 通过 Vault / Secrets Manager 分发            │
│   ✓ 每人独立凭证，可追踪操作                      │
│   ✓ 凭证有过期时间，定期轮转                      │
│   ✓ 使用 OIDC 实现免凭证分发                      │
│   ✓ 每个团队/环境使用独立 kubeconfig              │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 推荐的最终方案

对于大多数团队，推荐的组合是：

```
Dex (OIDC Provider)
  └── 对接企业 LDAP / GitHub / GitLab SSO
      └── kubelogin (exec 插件)
          └── 每人一份无密钥 kubeconfig 模板
              └── RBAC 按 OIDC Group 映射
                  └── 用户登录时自动获取短期 Token
                      └── Token 过期自动刷新（refresh_token）
```

**这样做的好处：** 你分发的 kubeconfig 文件中**不包含任何秘密凭证**，安全性大幅提高。即使文件泄露，攻击者也无法使用（需要用户的 SSO 身份才能获取 Token）。团队成员离职时，只需在 LDAP/SSO 中禁用账号即可，无需轮转任何 K8s 凭证。
