---
title: Docker 多阶段构建
date: 2026-08-16 20:45:00
tags:
  - Docker
  - 镜像优化
  - CI/CD
categories:
  - Docker
---

## 什么是多阶段构建？

多阶段构建（Multi-stage Build）是 Docker 17.05 引入的特性，允许你在一个 `Dockerfile` 中使用多个 `FROM` 指令，每个 `FROM` 开始一个新的构建阶段。核心思想是：**在一个阶段中编译构建，在另一个阶段中只拷贝最终产物**，从而大幅减小最终镜像的体积。

## 为什么需要它？

在多阶段构建出现之前，常见的做法是：

- **方式一**：把编译环境和运行环境都打包进同一个镜像 → 镜像臃肿（可能几个 GB）
- **方式二**：写两个 Dockerfile，先构建再拷贝产物 → 流程复杂，不易维护

多阶段构建完美解决了这两个问题。

## 基本语法

```dockerfile
# ========== 阶段 1：构建 ==========
FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o myapp .

# ========== 阶段 2：运行 ==========
FROM alpine:3.19

RUN apk --no-cache add ca-certificates tzdata
WORKDIR /app

# 只从 builder 阶段拷贝编译产物
COPY --from=builder /app/myapp .

EXPOSE 8080
CMD ["./myapp"]
```

关键点：
- `AS builder` 给阶段命名，方便后续引用
- `COPY --from=builder` 从指定阶段拷贝文件
- 最终镜像只包含 `alpine` + 一个二进制文件，体积可以从 **1 GB+ 缩减到 10 MB 左右**

## 实际示例：前端项目

```dockerfile
# ========== 阶段 1：构建前端资源 ==========
FROM node:20-alpine AS build-stage

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
# 产物在 /app/dist 目录下

# ========== 阶段 2：用 Nginx 提供服务 ==========
FROM nginx:1.25-alpine

# 拷贝构建产物到 Nginx 的静态文件目录
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 拷贝自定义 Nginx 配置（可选）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

效果：最终镜像里没有 `node_modules`、源代码、构建工具链，只有 Nginx 和静态文件。

## 高级用法

### 1. 从外部镜像拷贝

`--from` 不一定引用当前 Dockerfile 中的阶段，也可以直接引用任意镜像：

```dockerfile
COPY --from=nginx:1.25-alpine /etc/nginx/nginx.conf /nginx.conf
```

### 2. 多阶段 + BuildKit 缓存挂载

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

FROM deps AS build
COPY . .
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

`--mount=type=cache` 可以跨构建缓存 `npm` 的下载内容，显著加速后续构建。

### 3. 只构建某个阶段

```bash
# 只执行到 builder 阶段（用于调试）
docker build --target builder -t myapp:debug .
```

## 体积对比

| 方案 | 镜像大小（典型值） |
|---|---|
| 不使用多阶段构建（golang:1.22 全量） | ~800 MB - 1.2 GB |
| 多阶段构建（alpine 运行时） | ~8 - 15 MB |
| 多阶段构建（distroless 运行时） | ~5 - 12 MB |

## 最佳实践

1. **用 `alpine` 或 `distroless` 作为最终运行时基础镜像**，体积最小、攻击面最小
2. **按依赖安装 → 拷贝源码 → 构建的顺序排列指令**，充分利用 Docker 层缓存
3. **给每个阶段命名**（`AS name`），提高可读性
4. **用 `.dockerignore` 排除不需要的文件**，减小构建上下文
5. **配合 CI/CD 使用 `--target`**，可以灵活地在不同阶段做不同的事（测试、构建、部署）

---

如果你有具体的项目场景，我可以帮你写一个针对性的 Dockerfile。
