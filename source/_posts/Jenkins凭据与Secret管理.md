---
title: Jenkins 凭据与 Secret 管理
date: 2026-08-23 12:45:00
tags:
  - Jenkins
  - 凭据
  - Secret
categories:
  - Jenkins SRE
---

Jenkins 凭据是 CI 安全核心，需加密存储、最小权限与外部 Secret 集成。

## 凭据类型

| 类型 | 用途 |
|------|------|
| Username/Password | Git、Harbor |
| SSH Key | Git SSH、远程部署 |
| Secret text | API Token |
| Secret file | kubeconfig、证书 |
| Certificate | TLS |

## Pipeline 使用

```groovy
pipeline {
    environment {
        REGISTRY_CREDS = credentials('harbor-registry')
    }
    stages {
        stage('Push') {
            steps {
                sh '''
                  echo $REGISTRY_CREDS_PSW | docker login registry.example.com \
                    -u $REGISTRY_CREDS_USR --password-stdin
                '''
            }
        }
    }
}
```

## 凭据域（Credentials Domain）

```
Folder 级凭据隔离：
  team-a/* → 仅 team-a Job 可用
  team-b/* → 仅 team-b Job 可用
```

## 加密原理

```
secrets/master.key + hudson.util.Secret → 加密 credentials.xml
```

**备份必须含 secrets/ 目录**，否则凭据不可解密。

## 外部 Secret 集成

| 方案 | 说明 |
|------|------|
| K8s Credentials Provider | 从 K8s Secret 同步 |
| HashiCorp Vault Plugin | 动态凭据 |
| AWS Secrets Manager | 云环境 |

```groovy
// Vault 示例
def secrets = [[path: 'secret/data/ci/registry', secretValues: [
    [vaultKey: 'username', envVar: 'REG_USER'],
    [vaultKey: 'password', envVar: 'REG_PASS'],
]]]
withVault([vaultSecrets: secrets]) {
    sh 'docker login ...'
}
```

## 轮换

```
1. 新凭据写入 Vault/K8s
2. Jenkins 更新或自动同步
3. 验证 Pipeline
4. 作废旧凭据
```

## 禁止

- Jenkinsfile 硬编码 token
- 日志打印凭据环境变量
- 全局凭据给所有 Job

## Checklist

- [ ] Folder 级凭据隔离
- [ ] master.key 备份安全
- [ ] 优先 Vault/K8s 外部化
- [ ] 季度凭据 audit
- [ ] Mask Passwords 插件

凭据泄露 = **供应链风险**，与 **Python/K8s SRE** 密钥管理对齐。
