---
title: Linux 公钥分发底层细节
date: 2026-09-08 11:45:00
tags:
  - Linux
  - SSH
  - 安全
  - 密钥管理
categories:
  - Linux
---

## 一、密钥对生成过程

### 1.1 SSH 密钥生成的底层原理

`ssh-keygen` 底层调用的是 **OpenSSL/libcrypto** 或 **OpenSSH 内置的加密库**，核心流程如下：

```
熵源收集 → 伪随机数生成器(PRNG) → 私钥参数生成 → 公钥数学推导 → 序列化存储
```

**以 RSA 为例的具体步骤：**

```
1. 从 /dev/urandom 或 getrandom() 系统调用获取密码学安全随机数
2. 使用随机数生成两个大素数 p 和 q（各 2048/4096 位）
3. 计算 n = p × q（模数）
4. 计算 φ(n) = (p-1)(q-1)（欧拉函数）
5. 选择公钥指数 e = 65537 (0x10001)
6. 计算私钥指数 d = e⁻¹ mod φ(n)（模逆运算）
7. 公钥 = (e, n)  → 存储为 id_rsa.pub
8. 私钥 = (d, n, p, q, dp, dq, qinv) → 存储为 id_rsa
```

**密钥文件的内部结构：**

```bash
# 私钥文件 (PEM/ASN.1 DER 编码)
-----BEGIN OPENSSH PRIVATE KEY-----    # OpenSSH 新格式
# 头部魔数: "openssh-key-v1\0"
# 字段: ciphername, kdfname, kdfoptions, numkeys
# 每个密钥: pubkey_blob, privkey_blob
# privkey_blob 包含: checkint1, checkint2, keytype, n, e, d, iqmp, p, q, comment, padding
-----END OPENSSH PRIVATE KEY-----

# 公钥文件 (单一一行)
# wire format: [长度(4字节) | "ssh-rsa"(类型) | e(大整数) | n(大整数)] → base64编码
ssh-rsa AAAAB3NzaC1yc2... user@host
```

**Ed25519 的差异：**

```
1. 使用 Curve25519 椭圆曲线（非 NIST 曲线）
2. 私钥 = 32 字节随机种子
3. 公钥 = 私钥经 SHA-512 哈希后与基点做标量乘法的结果
4. 生成速度极快，签名更短（64 字节）
```

### 1.2 底层系统调用链

```
ssh-keygen
  → arc4random_buf() / getrandom(GRND_RANDOM)    # 获取熵
  → RSA_generate_key_ex() / ED25519_keypair()     # 密钥生成
  → PEM_write_PrivateKey() / sshkey_write()       # 序列化
  → open("id_rsa", O_WRONLY|O_CREAT|O_EXCL, 0600) # 写文件（权限严格限制为 600）
  → fchmod(fd, 0600)                               # 再次确认权限
```

---

## 二、公钥分发的核心机制

### 2.1 `~/.ssh/authorized_keys` 文件

这是最基础的分发方式，底层本质是一个**文件系统级别的访问控制列表**：

```bash
# 文件路径及权限要求（sshd 会严格检查）
~/.ssh/                # 权限必须为 700 (drwx------)
~/.ssh/authorized_keys # 权限必须为 600 (-rw-------)
~home目录              # 不能被其他用户写 (权限检查向上递归)
```

**sshd 源码中的权限检查逻辑（auth.c / auth2-pubkey.c）：**

```c
// 伪代码还原
secure_filename(uid, path, ...) {
    // 1. 从文件向根目录逐级检查
    // 2. 确保路径中每个目录的 owner 要么是 root，要么是目标用户
    // 3. 确保没有其他用户有写权限
    // 4. 这是为了防止攻击者通过符号链接或目录劫持注入公钥
}
```

**authorized_keys 的每一行格式：**

```
[选项字段] keytype base64-key-data [注释]
```

**选项字段的底层解析：**

```
# sshd 源码中 auth-options.c 的解析逻辑
# 每个选项是一个 key=value 或 flag 形式，逗号分隔

# 完整示例：
command="/usr/bin/restricted",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-rsa AAAA...

# 支持的选项及其底层效果：
command="cmd"     → 将用户连接强制转为执行 cmd（通过 FORCED_COMMAND 环境变量）
from="10.0.0.0/24" → 校验客户端 IP 地址（sockaddr 比较）
expiry-time="20261231" → 检查 time() 比较，过期则拒绝
environment="KEY=VAL"  → setenv()（需要 sshd_config 中 PermitUserEnvironment yes）
```

### 2.2 `ssh-copy-id` 的底层操作

```bash
#!/bin/bash
# ssh-copy-id 的核心逻辑（简化还原）

# 1. 读取本地公钥
identity_file="~/.ssh/id_rsa.pub"

# 2. 通过 SSH 连接目标机器（此时用密码认证）
# 3. 在远程执行 shell 命令

# 底层实际传输过程（在远程执行）:
REMOTE_COMMAND='
  mkdir -p ~/.ssh &&          # 创建目录
  chmod 700 ~/.ssh &&         # 设置权限
  cat >> ~/.ssh/authorized_keys &&  # 追加公钥（不覆盖已有密钥）
  chmod 600 ~/.ssh/authorized_keys  # 设置文件权限
'
```

**关键细节：整个公钥内容通过 SSH 连接的 stdin 传输，而非 scp 文件。**

---

## 三、SSH 认证握手的底层流程

### 3.1 完整的公钥认证握手（RFC 4252）

```
客户端                                              服务端
  |                                                   |
  |  ①  TCP 三次握手                                    |
  |  ─────────────────────────────────────────────→    |
  |                                                   |
  |  ②  SSH 版本交换                                    |
  |  ←─────────────────────────────────────────────    |
  |  "SSH-2.0-OpenSSH_9.0\r\n"                        |
  |                                                   |
  |  ③  密钥交换 (SSH Key Exchange, RFC 4253 §7)       |
  |  ──── KEXINIT (算法协商) ──────────────────────→   |
  |  ←─── KEXINIT ─────────────────────────────────    |
  |  ──── DH_INIT (Diffie-Hellman 公钥) ──────────→   |
  |  ←─── DH_REPLY (服务端主机密钥 + DH公钥+签名)───    |
  |                                                   |
  |  此时双方已有共享会话密钥 (session key)              |
  |  后续所有通信对称加密 (AES-256-GCM 等)              |
  |                                                   |
  |  ④  用户认证请求                                    |
  |  ──── SSH_MSG_USERAUTH_REQUEST ───────────────→   |
  |       method: "publickey"                         |
  |       algorithm: "rsa-sha2-256"                   |
  |       has_sig: FALSE  ← 注意：第一次不带签名        |
  |                                                   |
  |  ←─── SSH_MSG_USERAUTH_PK_OK ─────────────────    |
  |       (服务端确认：这个公钥在 authorized_keys 中)    |
  |                                                   |
  |  ⑤  带签名的认证请求                                |
  |  ──── SSH_MSG_USERAUTH_REQUEST ───────────────→   |
  |       method: "publickey"                         |
  |       has_sig: TRUE                               |
  |       signature: Sign(session_id || auth_msg)     |
  |       ↑ 用本地私钥对会话数据签名                     |
  |                                                   |
  |  ←─── SSH_MSG_USERAUTH_SUCCESS ──────────────    |
  |       (服务端用公钥验签成功，认证通过)               |
  |                                                   |
```

### 3.2 步骤④-⑤ 的底层实现细节

**服务端验证逻辑（auth2-pubkey.c 中的核心路径）：**

```c
// 伪代码还原 sshd 的公钥认证核心路径
userauth_pubkey(Authctxt *authctxt, sshbuf *b) {
    // 1. 从消息中解析算法类型和公钥
    sshbuf_get_string(b, &pkalgo);      // 如 "ssh-ed25519"
    sshbuf_get_string(b, &pubkey_blob);  // 公钥的二进制表示
    
    // 2. 检查 has_sig 标志
    if (!has_sig) {
        // 阶段一：仅探测，不验证签名
        // 检查该公钥是否在用户 authorized_keys 中存在
        if (match_key_in_authorized_keys(authctxt->pw, key)) {
            // 发送 SSH_MSG_USERAUTH_PK_OK
            return 0;  // 等待客户端发送带签名的请求
        }
        return -1;
    }
    
    // 3. has_sig == TRUE，阶段二：验证签名
    sshbuf_get_string(b, &signature);
    
    // 4. 构造签名数据: session_id || userauth_request_msg
    //    这绑定了当前会话，防止重放攻击
    sshbuf_put_string(sigbuf, session_id, session_id_len);
    sshbuf_put_string(sigbuf, auth_request_without_sig);
    
    // 5. 用公钥验证签名
    result = sshkey_verify(key, signature, sigbuf, NULL);
    
    // 6. 验证 authorized_keys 中的附加限制
    check_auth_options(auth_options, user_pw);
    // 检查 from=, command=, expiry-time= 等
    
    return result == 0 ? 1 : -1;  // 1=成功, -1=失败
}
```

**签名中绑定的完整数据结构：**

```
签名输入 = session_id           // 密钥交换时确定的会话标识
         || byte SSH_MSG_USERAUTH_REQUEST
         || string user_name
         || string service_name ("ssh-connection")
         || string "publickey"
         || boolean TRUE
         || string algorithm
         || string public_key_blob
```

**为什么分两步（先探测后签名）？**

```
这是一个性能优化：
- 每台机器可能配置了多个公钥（如 5 个）
- 客户端先发送"我想用这个公钥登录"（不带签名）
- 服务端快速查表确认该密钥是否被授权
- 如果不在列表中，客户端立即切换到下一个密钥
- 避免了用每个私钥都做一次昂贵的签名操作
```

### 3.3 主机密钥验证的底层细节

**`~/.ssh/known_hosts` 的存储格式：**

```
# 格式1: 哈希格式（默认，防枚举扫描）
|1|base64(salt)|base64(HMAC-SHA1(salt, hostname)) ssh-rsa AAAA...

# 格式2: 明文格式
192.168.1.100 ssh-rsa AAAA...
*.example.com ssh-ed25519 AAAA...

# 格式3: 证书机构（CA）
@cert-authority *.example.com ssh-rsa AAAA...（CA公钥）
```

**哈希格式的计算（hostkeys.c）：**

```c
// 存储时：
hmac_sha1_ctx = HMAC_CTX_new();
HMAC_Init(hmac_sha1_ctx, salt, 20);     // 随机 salt
HMAC_Update(hmac_sha1_ctx, hostname, len);
HMAC_Final(hmac_sha1_ctx, hash, &hashlen);

// 比较时：
// 从文件读取 salt → 对传入的 hostname 计算 HMAC → 与存储的哈希比较
// 优势：即使 known_hosts 泄露，攻击者也无法反推出连接过哪些主机
```

**首次连接的信任锚点（TOFU - Trust On First Use）：**

```
第一次连接未知主机时：
1. ssh 客户端弹出指纹确认提示
2. 指纹 = SHA256(host_key_blob)  → "SHA256:xxxxxxxx"
3. 用户确认后，公钥写入 known_hosts
4. 后续连接时：提取服务端主机密钥 → 与 known_hosts 比对
5. 不匹配则警告 "MAN IN THE MIDDLE ATTACK" 并拒绝连接
```

---

## 四、SSHFP 记录：DNS 分发主机公钥

### 4.1 原理

通过 DNS 记录分发主机公钥指纹，解决 TOFU 模型的信任问题（RFC 6594）：

```bash
# DNS 记录格式
# SSHFP  <algorithm> <fp_type> <fingerprint>
$ORIGIN example.com.
ssh-host  IN  SSHFP  4 2 2b10d8321b...(Ed25519, SHA-256)
ssh-host  IN  SSHFP  1 1 a1b2c3d4e5...(RSA, SHA-1)
```

**底层验证流程：**

```
1. SSH 客户端收到服务端主机密钥
2. 查询 DNS: SSHFP 记录（需要 DNSSEC 支持）
3. 如果 DNSSEC 验证通过：
   - 计算收到的主机密钥的指纹
   - 与 SSHFP 记录比对
   - 匹配 → 直接信任，不弹 TOFU 提示
4. 如果没有 DNSSEC：
   - SSHFP 记录本身可能被篡改
   - 回退到 known_hosts 逻辑
```

**配置启用：**

```bash
# ~/.ssh/config 或 /etc/ssh/ssh_config
Host *
    VerifyHostKeyDNS yes   # 启用 SSHFP 验证
    # yes = 先查 SSHFP，再查 known_hosts
    # no  = 仅查 known_hosts（默认）
```

---

## 五、SSH 证书认证：大规模公钥分发

### 5.1 问题与动机

```
传统 authorized_keys 的痛点：
- 1000 台服务器 × 500 用户 = 500,000 条公钥需要分发
- 用户离职需要逐台服务器删除公钥
- 没有过期时间机制
- 无法做细粒度的权限声明
```

### 5.2 SSH 证书的底层结构

```
SSH 证书 ≠ X.509 证书（OpenSSH 自有格式，DER 编码）

用户证书 (SSH_MSG_USERCERT) 结构：
┌─────────────────────────────────────────┐
│ type: "ssh-user-cert"                    │
│ serial: 唯一序列号                        │
│ key_id: "alice@company.com"              │
│ valid_principals: ["root", "alice"]      │  ← 允许登录的用户名
│ valid_after: 1700000000                  │  ← 有效期起始（Unix 时间戳）
│ valid_before: 1700604800                 │  ← 有效期截止
│ critical_options: {source-address: ...}  │  ← 强制约束
│ extensions: {permit-X11-forwarding: ""}  │  ← 非强制能力
│ CA 公钥                                  │
│ CA 签名 (对上述所有字段)                   │
└─────────────────────────────────────────┘
```

### 5.3 证书签发流程

```bash
# 1. 生成 CA 密钥对（受信任的签发方）
$ ssh-keygen -t ed25519 -f ca_user_key -C "User CA"

# 2. 用户生成本地密钥对
$ ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519

# 3. CA 对用户公钥签发证书
$ ssh-keygen -s ca_user_key \        # CA 私钥
    -I "alice@company.com" \          # key_id（用于审计）
    -n "alice,admin" \                # 允许登录的 principals
    -V "+52w" \                       # 有效期 52 周
    -z 1001 \                         # 序列号
    ~/.ssh/id_ed25519.pub             # 用户公钥

# 输出: id_ed25519-cert.pub（证书文件）
```

### 5.4 服务端验证证书的底层路径

```
服务端配置 (/etc/ssh/sshd_config):
    TrustedUserCAKeys /etc/ssh/ca_user_key.pub  # 信任的 CA 公钥

验证流程：
1. 客户端发送证书（而非原始公钥）
2. sshd 解析证书 DER 结构
3. 验证 CA 签名（用 TrustedUserCAKeys 中的公钥）
4. 检查 valid_after < now < valid_before
5. 检查证书中的 principals 是否包含请求的用户名
6. 检查 critical_options（如 source-address 限制源 IP）
7. 应用 extensions 中的权限控制
8. 全部通过 → SSH_MSG_USERAUTH_SUCCESS
```

```
优势：
- 服务端只需存储一个 CA 公钥，不需要逐用户分发
- 证书自带过期时间，自动失效
- 吊销通过证书序列号的 RevokedKeys 文件实现
- 可以签发针对特定主机集合的主机证书
```

---

## 六、GPG/包管理器的公钥分发

### 6.1 APT（Debian/Ubuntu）

```bash
# 密钥存储位置的演变
# 旧: /etc/apt/trusted.gpg（单一 keyring 文件，已弃用）
# 新: /etc/apt/trusted.gpg.d/ 和 /usr/share/keyrings/

# 添加仓库密钥的推荐方式（分离式）：
$ curl -fsSL https://repo.example.com/gpg.key | \
    gpg --dearmor -o /usr/share/keyrings/example-archive-keyring.gpg

# 在 sources.list 中绑定特定密钥：
deb [signed-by=/usr/share/keyrings/example-archive-keyring.gpg] \
    https://repo.example.com stable main
```

**APT 验证签名的底层流程：**

```
1. 下载 Release 文件 → 验证 Release.gpg（DETACHED 签名）
2. Release 文件包含所有 Packages 文件的 SHA256 哈希
3. 下载 Packages 文件 → 与 Release 中的哈希比对
4. Packages 文件包含每个 .deb 包的 SHA256 哈希
5. 下载 .deb 包 → 与 Packages 中的哈希比对
6. 这是一个信任链: GPG Key → Release → Packages → .deb
```

```bash
# 查看具体验证细节
$ apt-get update -o Debug::Acquire::gpgv=1
```

### 6.2 RPM（RHEL/Fedora）

```bash
# RPM 密钥导入
$ rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora

# 底层 keyring 位置
/var/lib/rpm/pubkeys.db   # Berkeley DB 格式

# 签名验证
$ rpm --checksig package.rpm
# 输出: RSA/SHA256 签名, OK
```

### 6.3 验证链的底层对比

```
┌──────────┬──────────────────┬───────────────────┐
│          │ APT (Debian)     │ RPM (Red Hat)      │
├──────────┼──────────────────┼───────────────────┤
│ 签名格式 │ OpenPGP (GPG)    │ OpenPGP (GPG)     │
│ 验证库   │ gpgv / libgcrypt │ rpm → libgcrypt   │
│ 信任链   │ Key→Release→     │ Key→Header→       │
│          │ Packages→deb     │ rpm payload        │
│ 密钥分发 │ signed-by 指定   │ 系统 keyring       │
└──────────┴──────────────────┴───────────────────┘
```

---

## 七、自动化的公钥分发方案

### 7.1 LDAP 集成

```
# 当 sshd 配置了 AuthorizedKeysCommand 或 LDAP 时
# 底层查询流程：

1. PAM/LDAP 模块连接 LDAP 服务器
2. 查询: (&(objectClass=posixAccount)(uid=alice))
3. 读取属性: sshPublicKey
4. 返回公钥用于认证

# LDAP schema 定义 (openssh-lpk.schema)
# 属性类型:
attributetype ( 1.3.6.1.4.1.24552.500.1.1.1.13
    NAME 'sshPublicKey'
    DESC 'OpenSSH Public Key'
    EQUALITY octetStringMatch
    SYNTAX 1.3.6.1.4.1.1466.115.121.1.40 )

# 用户 LDAP 条目:
dn: uid=alice,ou=People,dc=example,dc=com
objectClass: posixAccount
objectClass: ldapPublicKey
uid: alice
sshPublicKey: ssh-ed25519 AAAA...
```

**sshd 配置：**

```bash
# /etc/ssh/sshd_config
AuthorizedKeysCommand /usr/bin/sss_ssh_authorizedkeys
AuthorizedKeysCommandUser nobody
# 底层：sshd fork 子进程，以 nobody 身份执行命令
# 命令输出格式与 authorized_keys 完全一致
```

### 7.2 HashiCorp Vault SSH 签名

```
# 使用 Vault 作为 CA 的动态证书签发

流程：
1. 用户向 Vault 请求短期 SSH 证书
2. Vault 验证用户身份（LDAP/OIDC/Token）
3. Vault 用 CA 私钥签发证书（有效期如 1 小时）
4. 用户用证书登录目标服务器
5. 服务器信任 Vault 的 CA 公钥
6. 证书自动过期，无需吊销管理

# Vault API 调用细节
$ vault write -format=json ssh-client-signer/sign/my-role \
    public_key=@$HOME/.ssh/id_ed25519.pub \
    valid_principals="alice" \
    ttl="1h"
    
# 返回的签名证书写入 ~/.ssh/id_ed25519-cert.pub
```

---

## 八、底层安全保护机制

### 8.1 SSH Agent 的密钥管理

```
# ssh-agent 的工作原理（Unix Domain Socket）

1. ssh-agent 启动 → 创建 Unix socket (如 /tmp/ssh-XXXX/agent.12345)
2. 设置环境变量: SSH_AUTH_SOCK=/tmp/ssh-XXXX/agent.12345
3. ssh 客户端通过该 socket 与 agent 通信

# 协议消息:
SSH_AGENTC_REQUEST_IDENTITIES    → 请求列出所有密钥
SSH_AGENT_IDENTITIES_ANSWER      → 返回公钥列表
SSH_AGENTC_SIGN_REQUEST          → 请求对数据签名（私钥不出 agent）
SSH_AGENT_SIGN_RESPONSE          → 返回签名结果

# 关键：私钥永远不离开 agent 进程的内存空间
# 签名操作在 agent 内完成，只有签名结果传回客户端
```

**ssh-agent 的内存保护：**

```c
// OpenSSH 中的内存锁定
#ifdef HAVE_MLOCK
mlock(sensitive_data, len);      // 防止交换到磁盘
#endif
// 密钥使用完后
explicit_bzero(sensitive_data, len);  // 安全擦除（防止编译器优化掉清零）
```

### 8.2 PKCS#11 硬件密钥

```
# 当使用智能卡/硬件安全模块时
$ ssh-keygen -D /usr/lib64/pkcs11/opensc-pkcs11.so

# 底层调用链:
ssh → PKCS#11 API → C_Sign() → 硬件安全模块
# 私钥存储在硬件中，无法导出
# 签名操作在硬件内部的防篡改芯片中完成
```

### 8.3 FIDO2/U2F 安全密钥（sk 类型）

```bash
# OpenSSH 8.2+ 支持的硬件安全密钥
$ ssh-keygen -t ed25519-sk -O resident    # 密钥常驻设备
$ ssh-keygen -t ecdsa-sk -O verify-required # 需要触摸确认

# 底层交互（通过 libfido2）:
ssh → libhidapi → USB HID → FIDO2 安全密钥设备
# CTAP2 协议: authenticatorMakeCredential / authenticatorGetAssertion
# 私钥永远在安全密钥的安全区 (secure element) 中
```

---

## 九、总结：信任传递的全景图

```
┌─────────────────────────────────────────────────────────┐
│                    公钥分发的信任模型                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  方案              信任基础           适用规模            │
│  ─────────────────────────────────────────────────────  │
│  authorized_keys   文件系统 ACL       小规模 (<100台)     │
│  ssh-copy-id       初始密码信任       一次性引导           │
│  known_hosts (TOFU)首次连接信任       通用               │
│  SSHFP + DNSSEC    DNS 层 PKI        有 DNSSEC 的环境    │
│  SSH 证书          CA 中心化信任      大规模企业           │
│  LDAP              目录服务           已有 LDAP 基础设施   │
│  Vault 签名        动态短期证书       云原生/零信任        │
│  GPG 包签名        发行版信任链       软件包分发           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

每一种分发机制的底层都围绕同一个核心问题：**如何让通信双方安全地交换并信任公钥材料，同时抵抗中间人攻击**。从最简单的 authorized_keys 文件权限检查，到 SSH 证书的 DER 编码签发，再到 FIDO2 硬件的安全区保护，本质上都是在不同信任假设下对这个问题的不同回答。
