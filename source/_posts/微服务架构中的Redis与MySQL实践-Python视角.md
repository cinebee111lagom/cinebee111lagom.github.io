---
title: 微服务架构中的 Redis 与 MySQL 实践（Python 视角）
date: 2026-09-07 10:15:00
tags:
  - Redis
  - MySQL
  - 微服务
  - Python
categories:
  - 缓存架构
---

## 一、整体架构概览

在微服务架构中，**MySQL** 通常作为持久化存储（主数据库），**Redis** 则承担缓存、会话管理、消息队列等职责。两者配合使用，是后端开发中最经典的组合之一。

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ 用户服务  │     │ 订单服务  │     │ 商品服务  │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     ├────────┬───────┼────────┬───────┤
     ▼        ▼       ▼        ▼       ▼
  ┌──────┐  ┌─────┐ ┌──────┐ ┌─────┐
  │Redis │  │MySQL│ │Redis │ │MySQL│  ...
  │(缓存) │  │(存储)│ │(队列) │ │(存储)│
  └──────┘  └─────┘ └──────┘ └─────┘
```

---

## 二、MySQL 在微服务中的角色

### 1. 核心职责
- 持久化存储业务数据（用户信息、订单、商品等）
- 保证数据的 **ACID** 特性
- 每个微服务拥有**独立的数据库**（Database per Service 模式）

### 2. Python 中常用的 ORM/驱动

```python
# SQLAlchemy（最主流）
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine("mysql+pymysql://user:pass@localhost:3306/order_db")
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    amount = Column(Numeric(10, 2))
    status = Column(String(20), default="pending")
```

```python
# aiomysql（异步场景，适合 FastAPI）
import aiomysql

async def get_order(order_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
            return await cur.fetchone()
```

---

## 三、Redis 在微服务中的角色

Redis 在微服务中主要承担以下职责：

| 场景 | 说明 | Redis 数据结构 |
|------|------|---------------|
| **缓存层** | 缓存热点数据，减轻 MySQL 压力 | String / Hash |
| **分布式会话** | 存储用户 Session | String / Hash |
| **分布式锁** | 防止并发重复操作 | String (SETNX) |
| **消息队列** | 服务间异步通信 | List / Stream |
| **限流/计数器** | API 限流、访问计数 | String (INCR) |
| **排行榜/计分** | 排序类业务 | Sorted Set |

### Python 中常用驱动

```python
# 同步 - redis-py
import redis

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
r.set("user:1001:name", "张三", ex=3600)  # 1小时过期
name = r.get("user:1001:name")
```

```python
# 异步 - aioredis（推荐配合 FastAPI）
import redis.asyncio as aioredis

redis_client = aioredis.from_url("redis://localhost:6379")

async def get_cached_user(user_id: int):
    cached = await redis_client.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    # 缓存未命中，查 MySQL
    user = await db_fetch_user(user_id)
    await redis_client.set(f"user:{user_id}", json.dumps(user), ex=1800)
    return user
```

---

## 四、经典模式：Cache-Aside（旁路缓存）

这是 Redis + MySQL 最常用的缓存策略：

```python
async def get_product(product_id: int):
    cache_key = f"product:{product_id}"
    
    # 1. 先查 Redis 缓存
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 2. 缓存未命中，查 MySQL
    product = await mysql_fetch("SELECT * FROM products WHERE id=%s", (product_id,))
    if not product:
        # 缓存空值，防止缓存穿透
        await redis.set(cache_key, json.dumps(None), ex=60)
        return None
    
    # 3. 写入缓存
    await redis.set(cache_key, json.dumps(product), ex=1800)
    return product
```

### 需要注意的问题

| 问题 | 说明 | 解决方案 |
|------|------|---------|
| **缓存穿透** | 查询不存在的数据，每次都打到 DB | 缓存空值 / 布隆过滤器 |
| **缓存击穿** | 热点 key 过期，大量请求同时打到 DB | 互斥锁 / 永不过期+异步刷新 |
| **缓存雪崩** | 大量 key 同时过期 | 过期时间加随机值 |

---

## 五、分布式锁示例（Python + Redis）

在微服务中，当多个实例可能同时操作同一资源时，需要分布式锁：

```python
import redis.asyncio as redis
import uuid
import asyncio

class RedisLock:
    def __init__(self, redis_client, key, expire=10):
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.token = str(uuid.uuid4())
        self.expire = expire

    async def acquire(self):
        return await self.redis.set(
            self.key, self.token, nx=True, ex=self.expire
        )

    async def release(self):
        # Lua 脚本保证原子性
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(lua_script, 1, self.key, self.token)

# 使用
async def create_order(user_id, product_id):
    lock = RedisLock(redis_client, f"order:{user_id}:{product_id}")
    if await lock.acquire():
        try:
            # 检查库存 → 扣减 → 创建订单（防重复下单）
            stock = await check_stock(product_id)
            if stock > 0:
                await deduct_stock(product_id)
                return await insert_order(user_id, product_id)
        finally:
            await lock.release()
```

---

## 六、微服务间通信 + Redis 作为消息队列

```python
# 生产者（订单服务）
async def publish_event(event_type: str, data: dict):
    await redis.xadd("events:stream", {"type": event_type, "data": json.dumps(data)})

# 消费者（库存服务）
async def consume_events():
    while True:
        messages = await redis.xread(
            {"events:stream": "$"}, count=10, block=5000
        )
        for stream, entries in messages:
            for msg_id, fields in entries:
                event = json.loads(fields["data"])
                await handle_event(fields["type"], event)
                await redis.xack("events:stream", "inventory_group", msg_id)
```

---

## 七、技术选型建议

| 维度 | 推荐方案 |
|------|---------|
| Web 框架 | **FastAPI**（异步，高性能） |
| MySQL ORM | **SQLAlchemy 2.0**（异步支持）或 **Tortoise ORM** |
| Redis 驱动 | **redis-py** (async mode) |
| 微服务框架 | **FastAPI + gRPC** 或 **Nameko** |
| 配置中心 | Consul / Nacos / etcd |
| 服务注册发现 | Consul + python-consul |

---

**总结：** MySQL 保证数据可靠，Redis 提升访问速度。在 Python 微服务中，关键是根据业务场景选择合适的缓存策略，处理好缓存一致性问题，并善用 Redis 的多种数据结构来解决分布式环境下的实际问题。
