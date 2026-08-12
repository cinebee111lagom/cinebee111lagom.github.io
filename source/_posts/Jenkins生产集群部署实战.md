---
title: Jenkins 生产集群部署实战
date: 2026-08-23 09:30:00
tags:
  - Jenkins
  - 部署
categories:
  - Jenkins SRE
---

生产 Jenkins 推荐 **Controller HA + 共享 JENKINS_HOME + 独立 Agent**。

## Controller 部署（Docker 示例）

```yaml
# docker-compose.yml
services:
  jenkins:
    image: jenkins/jenkins:2.440.3-lts-jdk17
    user: root
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - jenkins_home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - JAVA_OPTS=-Djenkins.install.runSetupWizard=false
        -Xms2g -Xmx4g
        -Dhudson.model.DirectoryBrowserSupport.CSP=

volumes:
  jenkins_home:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nfs.example.com,rw
      device: ":/exports/jenkins"
```

生产 JENKINS_HOME 必须 **NFS/EFS/块存储**，非本地盘。

## 初始配置

```bash
# 首次启动获取 admin 密码
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword

# 安装推荐插件 + 额外：
# - Pipeline、Blue Ocean、Kubernetes、Configuration as Code
# - Prometheus metrics、Job Configuration History
```

## JVM 参数

```bash
JAVA_OPTS="-Xms2g -Xmx4g \
  -XX:+UseG1GC \
  -Dhudson.model.LoadStatistics.clock=10000 \
  -Djenkins.model.Jenkins.slaveAgentPort=50000"
```

## 反向代理（Nginx）

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300;
}
```

## 静态 Agent 连接

```bash
# Agent 节点
curl -sO http://jenkins:8080/jnlpJars/agent.jar
java -jar agent.jar -url http://jenkins:8080/ -secret <token> -name agent-1 -workDir /data/jenkins
```

## 检查清单

- [ ] JENKINS_HOME 共享存储（HA 场景）
- [ ] JDK 17、LTS 镜像
- [ ] HTTPS 反代
- [ ] Agent 端口 50000 内网可达
- [ ] 初始 wizard 完成后创建非 admin 账号

**Controller 不做重构建**，仅调度与 UI。
