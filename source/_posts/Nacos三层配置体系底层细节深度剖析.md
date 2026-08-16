---
title: Nacos 三层配置体系底层细节深度剖析
date: 2026-09-07 18:45:00
tags:
  - Nacos
  - Spring Cloud
  - 配置中心
  - 微服务
categories:
  - 微服务
---

## 一、三层配置的本质：一条完整的配置合并链

很多人以为 shared-configs、extension-configs、应用专属配置只是"分组不同"，其实它们在底层经历了一套完全不同的加载顺序、优先级规则和合并策略。

```
最终生效的 Environment = 合并后的 PropertySources 链

优先级从高到低（后面的会覆盖前面的同名 key）：

┌──────────────────────────────────────────────────────┐
│ ① commandLineArgs                (--key=value)       │
├──────────────────────────────────────────────────────┤
│ ② systemProperties               (-Dkey=value)      │
├──────────────────────────────────────────────────────┤
│ ③ systemEnvironment              (ENV_KEY=value)    │
├──────────────────────────────────────────────────────┤
│ ④ applicationConfig: [bootstrap.yml]                 │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌── 以下为 NacosPropertySourceLocator 注入 ──┐     │
│  │                                            │     │
│  │ ⑤ 应用专属配置（最高 Nacos 优先级）          │     │
│  │    order-service.yaml                      │     │
│  │                                            │     │
│  │ ⑥ extension-configs（第二优先级）            │     │
│  │    seata-config.yaml                       │     │
│  │    sentinel-rules.json                     │     │
│  │                                            │     │
│  │ ⑦ shared-configs（最低 Nacos 优先级）        │     │
│  │    common-logging.yaml                     │     │
│  │    common-redis.yaml                       │     │
│  │    common-datasource.yaml                  │     │
│  │                                            │     │
│  └────────────────────────────────────────────┘     │
│                                                      │
├──────────────────────────────────────────────────────┤
│ ⑧ applicationConfig: [application-prod.yml]          │
├──────────────────────────────────────────────────────┤
│ ⑨ applicationConfig: [application.yml]               │
├──────────────────────────────────────────────────────┤
│ ⑩ defaultProperties                                  │
└──────────────────────────────────────────────────────┘

关键规则：Nacos 配置 ⑤⑥⑦ 全部高于本地 yml ⑧⑨
这意味着 Nacos 的配置可以覆盖本地 application.yml 中的任何值
```



---

## 二、NacosPropertySourceLocator 的加载源码细节

这是整个三层配置的入口。Spring Cloud 在 Bootstrap 阶段调用 `locate()` 方法：

```java
public class NacosPropertySourceLocator implements PropertySourceLocator {

    private NacosConfigProperties nacosConfigProperties;
    private ConfigService configService;

    @Override
    public PropertySource<?> locate(Environment env) {
        
        // 将 application.yml 中的 spring.cloud.nacos.config.* 
        // 绑定到 NacosConfigProperties 对象
        nacosConfigProperties = NacosConfigPropertiesBuilder.build(env);
        
        // 创建 ConfigService 客户端（连接 Nacos Server）
        configService = nacosConfigServiceBuilder.build(nacosConfigProperties);
        
        // 创建一个复合配置源，所有 Nacos 配置都往里面加
        CompositePropertySource composite = new CompositePropertySource("NACOS");
        
        // ========================================
        // 第一步：加载 shared-configs（优先级最低）
        // ========================================
        loadSharedConfigs(composite);
        
        // ========================================
        // 第二步：加载 extension-configs（优先级中等）
        // ========================================
        loadExtensionConfigs(composite);
        
        // ========================================
        // 第三步：加载应用专属配置（优先级最高）
        // ========================================
        loadApplicationConfig(composite);
        
        return composite;  // 返回给 Bootstrap Context 合并
    }
}
```

**核心问题：composite.addPropertySource 的顺序决定了优先级**

```java
// PropertySource 的查找机制
// Spring 从 propertySources 列表的头部开始遍历
// 先找到的值直接返回，后面的同名 key 被忽略
// 所以：后加入 composite 的 PropertySource 优先级更高

// composite 内部结构（addPropertySource 顺序）：
CompositePropertySource composite;
│
├── [0] NacosPropertySource  common-datasource.yaml  ← 最先添加，优先级最低
├── [1] NacosPropertySource  common-redis.yaml
├── [2] NacosPropertySource  common-logging.yaml
├── [3] NacosPropertySource  seata-config.yaml       ← extension 后加
├── [4] NacosPropertySource  sentinel-rules.json
├── [5] NacosPropertySource  order-service.yaml       ← 最后添加，优先级最高
│
│  查找 "spring.datasource.url" 时：
│  先查 [5] order-service.yaml → 有值？返回！
│  没有 → 查 [4] → 没有 → ... → 查 [0] common-datasource.yaml → 找到！
```

---

## 三、每一层配置的加载细节

### 1. shared-configs 加载

```java
private void loadSharedConfigs(CompositePropertySource composite) {
    List<NacosConfigProperties.Config> sharedConfigs = 
        nacosConfigProperties.getSharedConfigs();
    
    // shared-configs 按列表顺序加载
    // 先加的优先级低，后加的优先级高
    for (Config sharedConfig : sharedConfigs) {
        loadNacosDataIdIfPresent(
            composite,
            sharedConfig.getDataId(),      // "common-datasource.yaml"
            sharedConfig.getGroup(),        // "SHARED_GROUP"
            sharedConfig.getRefreshEnabled(), // true/false
            sharedConfig.getTimeout()
        );
    }
}
```

**配置文件 yml 中的定义：**

```yaml
spring:
  cloud:
    nacos:
      config:
        server-addr: nacos-server:8848
        namespace: production
        file-extension: yaml
        
        # shared-configs 配置
        shared-configs:
          - data-id: common-datasource.yaml
            group: SHARED_GROUP
            refresh: true          # 是否支持动态刷新
          - data-id: common-redis.yaml
            group: SHARED_GROUP
            refresh: true
          - data-id: common-logging.yaml
            group: SHARED_GROUP
            refresh: false         # 日志配置一般不需要动态刷新
```

**shared-configs 内部的加载流程：**

```
对每个 shared-config 项：

1. 构建 Nacos 配置标识
   dataId = "common-datasource.yaml"
   group  = "SHARED_GROUP"
   tenant = "production" (namespace ID)

2. 查询本地缓存
   ~/.nacos/config/NACOS-SHARED_GROUP/common-datasource.yaml_snapshot
   如果 Nacos Server 不可达 → 使用本地快照

3. HTTP 请求 Nacos Server
   GET /nacos/v1/cs/configs
   ? dataId=common-datasource.yaml
   & group=SHARED_GROUP
   & tenant=production-namespace-id
   
   返回：
   spring:
     datasource:
       url: jdbc:mysql://db-master:3306/order_db?useSSL=false
       username: order_user
       password: ENC(encrypted_password)
       hikari:
         maximum-pool-size: 20
         minimum-idle: 5
         connection-timeout: 30000

4. 解析 YAML → Properties → PropertySource
   "spring.datasource.url"     = "jdbc:mysql://db-master:3306/order_db"
   "spring.datasource.username" = "order_user"
   "spring.datasource.hikari.maximum-pool-size" = "20"
   
5. 封装为 NacosPropertySource 并加入 composite
   composite.addPropertySource(new NacosPropertySource(
       properties,        // Map<String, Object>
       "NACOS:common-datasource.yaml",
       nacosDataId,       // 标识来源
       refreshEnabled     // 是否注册监听器
   ))

6. 如果 refreshEnabled = true
   → 注册 Nacos Listener（长轮询监听变更）
```

### 2. extension-configs 加载

```java
private void loadExtensionConfigs(CompositePropertySource composite) {
    List<NacosConfigProperties.Config> extConfigs = 
        nacosConfigProperties.getExtensionConfigs();
    
    for (Config extConfig : extConfigs) {
        loadNacosDataIdIfPresent(
            composite,
            extConfig.getDataId(),       // "sentinel-rules.json"
            extConfig.getGroup(),         // "SENTINEL_GROUP"
            extConfig.getRefreshEnabled(),
            extConfig.getTimeout()
        );
    }
}
```

```yaml
spring:
  cloud:
    nacos:
      config:
        # extension-configs 配置
        extension-configs:
          - data-id: sentinel-rules.json
            group: SENTINEL_GROUP
            refresh: true
          - data-id: seata-config.yaml
            group: SEATA_GROUP
            refresh: true
```

**extension-configs 与 shared-configs 的区别：**

```
                  shared-configs              extension-configs
─────────────────────────────────────────────────────────────────
语义               多服务共享的基础配置          中间件/框架级配置
典型内容           数据源、Redis、日志          Sentinel规则、Seata配置
优先级             最低（在 Nacos 层）          中等
默认刷新           取决于单独设置               取决于单独设置
覆盖关系           被 extension 和 app 覆盖     被 app 配置覆盖
                                                      可覆盖 shared
```

**底层调用完全一致，区别仅在于加入 composite 的顺序：**

```java
// loadSharedConfigs 先调用 → 先加入 composite → 优先级低
// loadExtensionConfigs 后调用 → 后加入 composite → 优先级高
// loadApplicationConfig 最后调用 → 最后加入 → 优先级最高

// 最终 composite 内部顺序：
// [0] common-datasource.yaml    (shared, 最低)
// [1] common-redis.yaml         (shared)
// [2] common-logging.yaml       (shared)
// [3] sentinel-rules.json       (extension)
// [4] seata-config.yaml         (extension)
// [5] order-service.yaml        (app, 最高)
```

### 3. 应用专属配置加载

```java
private void loadApplicationConfig(CompositePropertySource composite) {
    
    // 构建 dataId
    // 方式一：使用 spring.application.name + file-extension
    // "order-service" + "." + "yaml" = "order-service.yaml"
    
    // 方式二：使用 nacos.config.name（自定义 dataId 前缀）
    
    // 方式三：支持多个 profile
    // 先加载 order-service.yaml（基础）
    // 再加载 order-service-prod.yaml（profile 覆盖）
    
    String dataId = buildDataId();
    String group = nacosConfigProperties.getGroup();  // "DEFAULT_GROUP"
    
    // 加载基础配置
    NacosPropertySource baseSource = loadNacosDataIdIfPresent(
        composite, dataId, group, true, timeout
    );
    
    // 加载 profile 配置
    for (String profile : env.getActiveProfiles()) {
        String profileDataId = dataId.replace(".yaml", "-" + profile + ".yaml");
        // 如 "order-service-prod.yaml"
        
        NacosPropertySource profileSource = loadNacosDataIdIfPresent(
            composite, profileDataId, group, true, timeout
        );
    }
}
```

**应用专属配置加载后的 composite 最终状态：**

```
composite 内部 PropertySource 列表：
│
├── [0] common-datasource.yaml       (shared)
│       spring.datasource.url=jdbc:mysql://master:3306/order_db
│       spring.datasource.hikari.maximum-pool-size=20
│
├── [1] common-redis.yaml            (shared)
│       spring.redis.host=redis-master
│       spring.redis.port=6379
│       spring.redis.lettuce.pool.max-active=16
│
├── [2] common-logging.yaml          (shared)
│       logging.pattern.console=%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n
│       logging.level.root=INFO
│
├── [3] sentinel-rules.json          (extension)
│       [{"resource":"/api/order/create","grade":1,"count":100}]
│
├── [4] seata-config.yaml            (extension)
│       seata.tx-service-group=my_tx_group
│       seata.service.vgroup-mapping.my_tx_group=default
│
├── [5] order-service.yaml           (app, 最高 Nacos 优先级)
│       server.port=8080
│       spring.datasource.url=jdbc:mysql://slave:3306/order_db  ← 覆盖 shared
│       order.max-items-per-page=50
│
└── [6] order-service-prod.yaml      (app profile)
        logging.level.root=WARN                               ← 覆盖 shared
        order.api-rate-limit=200
```

---

## 四、同名 Key 的覆盖机制深度剖析

这是最容易出错的地方。当多个配置源定义了同一个 key 时：

```
场景：spring.datasource.url 在三个地方都有定义

common-datasource.yaml (shared):
  spring.datasource.url: jdbc:mysql://master:3306/order_db

order-service.yaml (app):
  spring.datasource.url: jdbc:mysql://vip:3306/order_db?useSSL=true

application.yml (本地):
  spring.datasource.url: jdbc:mysql://localhost:3306/order_db

最终生效值：jdbc:mysql://vip:3306/order_db?useSSL=true  (app 配置)
原因：app 配置在 composite 中排最后，优先级最高
      本地 application.yml 的优先级低于整个 Nacos composite
```

**源码中的查找过程：**

```java
// CompositePropertySource.getProperty() 实际调用
public Object getProperty(String name) {
    // 遍历内部所有 PropertySource
    for (PropertySource<?> propertySource : this.propertySources) {
        Object value = propertySource.getProperty(name);
        if (value != null) {
            return value;  // 找到就立即返回，不继续往下找
        }
    }
    return null;
}

// 当查询 "spring.datasource.url" 时：
// [0] common-datasource → 返回 "jdbc:mysql://master:3306/order_db" → 但不返回！
//     等等，上面说的不对。composite 是从后往前查的！

// 正确的查找顺序：从 index 最大的开始（优先级最高）
// [6] order-service-prod.yaml → 没有这个 key → 继续
// [5] order-service.yaml → 找到！返回 "jdbc:mysql://vip:3306/order_db"

// 如果 [5] 也没有这个 key：
// [4] seata-config.yaml → 没有 → 继续
// [3] sentinel-rules.json → 没有 → 继续
// [2] common-logging.yaml → 没有 → 继续
// [1] common-redis.yaml → 没有 → 继续
// [0] common-datasource.yaml → 找到！返回 "jdbc:mysql://master:3306/order_db"
```

**注意：Spring 的 PropertySources 的查找顺序**

```java
// MutablePropertySources（Environment 内部）
// 查找时从头部开始（头部优先级最高）

// 但 CompositePropertySource 内部的子源列表
// 是从尾部开始查找（后添加的优先级高）

// 这两层查找方向相反，容易混淆：
// 第一层：Environment.propertySources 从头查找
//   → 先找 Nacos composite（整体优先级高）
//   → 再找 application.yml
// 第二层：composite 内部从尾查找
//   → 先找 app-config（优先级高）
//   → 再找 extension-configs
//   → 最后找 shared-configs（优先级低）
```

---

## 五、配置合并的数学模型

可以用集合论来理解配置合并：

```
设：
  S  = shared-configs 所有 key-value 的集合
  E  = extension-configs 所有 key-value 的集合
  A  = app-config 所有 key-value 的集合
  L  = 本地 application.yml 所有 key-value 的集合

合并规则：
  同名 key 时：A > E > S > L
  
  最终配置 = S ∪ E ∪ A ∪ L
  但对于重复 key：
    key ∈ S ∩ E → 取 E 的值
    key ∈ S ∩ A → 取 A 的值
    key ∈ E ∩ A → 取 A 的值
    key ∈ A ∩ L → 取 A 的值（Nacos > 本地）
    key ∈ S ∩ L → 取 S 的值（Nacos > 本地）

示例：
  S = {db.url: "master", db.pool: 20, cache.ttl: 3600}
  E = {sentinel.enabled: true, db.url: "ext-url"}
  A = {app.name: "order", db.url: "app-url", db.pool: 50}
  L = {db.url: "local", server.port: 8080}

  最终 = {
    db.url:         "app-url",         // A 覆盖 E 覆盖 S 覆盖 L
    db.pool:        50,                // A 覆盖 S
    cache.ttl:      3600,              // 仅在 S 中
    sentinel.enabled: true,            // 仅在 E 中
    app.name:       "order",           // 仅在 A 中
    server.port:    8080               // 仅在 L 中
  }
```

---

## 六、配置动态刷新的分层细节

不是所有配置都支持动态刷新，这由 `refresh` 字段控制：

```yaml
spring:
  cloud:
    nacos:
      config:
        shared-configs:
          - data-id: common-datasource.yaml
            refresh: true       # 支持动态刷新
          - data-id: common-redis.yaml
            refresh: true
          - data-id: common-logging.yaml
            refresh: false      # 不支持动态刷新
        extension-configs:
          - data-id: sentinel-rules.json
            refresh: true
          - data-id: seata-config.yaml
            refresh: true
        # 应用专属配置默认自动支持刷新（无需配置 refresh）
```

**refresh=true 时的底层监听注册：**

```java
private void loadNacosDataIdIfPresent(
        CompositePropertySource composite,
        String dataId, String group, 
        boolean refreshEnabled, long timeout) {
    
    // 1. 从 Nacos Server 拉取配置内容
    String config = configService.getConfig(dataId, group, timeout);
    
    // 2. 解析为 PropertySource 并加入 composite
    NacosPropertySource source = new NacosPropertySource(
        parseConfig(config), dataId, group, refreshEnabled
    );
    composite.addPropertySource(source);
    
    // 3. 如果 refresh=true，注册 Listener
    if (refreshEnabled) {
        registerListener(dataId, group, new Listener() {
            @Override
            public Executor getExecutor() {
                return null;  // 使用默认线程
            }
            
            @Override
            public void receiveConfigInfo(String configInfo) {
                // 收到配置变更通知
                
                // 更新内存中的 PropertySource
                NacosPropertySource existing = findPropertySource(dataId);
                existing.setProperties(parseConfig(configInfo));
                
                // 发布 RefreshEvent
                applicationContext.publishEvent(
                    new EnvironmentChangeEvent(changedKeys)
                );
                
                // 触发 @RefreshScope Bean 重建
                // 触发 @ConfigurationProperties 重新绑定
            }
        });
    }
    
    // 4. 如果 refresh=false，不注册 Listener
    //    配置变更后需要重启应用才能生效
}
```

**刷新生效的三种情况：**

```
┌─────────────────────────────────────────────────────────┐
│ 配置类型        │ refresh=true  │ refresh=false          │
├─────────────────────────────────────────────────────────┤
│ @Value          │ 自动更新 ✓    │ 需重启 ✗               │
│ @ConfigProps    │ 自动更新 ✓    │ 需重启 ✗               │
│ @RefreshScope   │ Bean 重建 ✓   │ 需重启 ✗               │
│ DataSource      │ 连接池重建 ✓  │ 需重启 ✗               │
│ Redis Config    │ 客户端重建 ✓  │ 需重启 ✗               │
│ 日志级别        │ 看框架实现     │ 需重启 ✗               │
└─────────────────────────────────────────────────────────┘
```

---

## 七、Nacos 配置加密的分层支持

不同层级的配置可以独立加密：

```yaml
# common-datasource.yaml (shared-configs)
spring:
  datasource:
    url: jdbc:mysql://master:3306/order_db
    username: ENC(ajK8sL2mN9pQ3rS5tU7vW1xY3zA5bC7dE9fG0hI2jK4)
    password: ENC(bC3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5zA7bC9d)
    # ENC(...) 是 Nacos 2.1+ 的加密标记
    # 密文由 Nacos Server 使用 AES-CBC 加密

# seata-config.yaml (extension-configs)  
seata:
  client:
    username: ENC(encrypted_seata_user)
    password: ENC(encrypted_seata_password)
```

**Nacos 加密的底层存储：**

```sql
-- config_info 表中的存储
SELECT data_id, content, encrypted_data_key 
FROM config_info 
WHERE data_id = 'common-datasource.yaml';

-- content 存储的是加密后的内容
-- encrypted_data_key 存储的是加密 AES 密钥本身（用 KMS 或密钥对保护）

-- 解密链路：
-- 1. 从 config_info 获取 encrypted_data_key
-- 2. 用 KMS 主密钥解密得到 AES 密钥
-- 3. 用 AES 密钥解密 content 中的 ENC(...) 部分
-- 4. 返回明文给客户端
```

---

## 八、配置拉取失败的降级策略

每层配置都有独立的降级机制：

```
配置加载过程中的故障处理：

应用启动
    │
    ├── 加载 shared-configs
    │   ├── common-datasource.yaml → Nacos Server 正常 → 获取配置 ✓
    │   ├── common-redis.yaml      → Nacos Server 超时 → 降级 ↓
    │   │                           ├── 查本地快照文件 → 找到 → 使用本地快照 ✓
    │   │                           └── 本地快照也没有 → 跳过该配置源 ⚠
    │   └── common-logging.yaml    → Nacos Server 正常 → 获取配置 ✓
    │
    ├── 加载 extension-configs
    │   ├── sentinel-rules.json    → Nacos Server 正常 → 获取配置 ✓
    │   └── seata-config.yaml      → Nacos Server 正常 → 获取配置 ✓
    │
    ├── 加载 app-config
    │   └── order-service.yaml     → Nacos Server 正常 → 获取配置 ✓
    │
    └── 合并完成，启动主 ApplicationContext

降级优先级：
  Nacos Server 返回配置 > 本地快照文件 > 跳过（使用更低优先级源的值）

本地快照路径：
  ~/.nacos/config/
  ├── NACOS-SHARED_GROUP/
  │   ├── common-datasource.yaml_snapshot
  │   ├── common-redis.yaml_snapshot
  │   └── common-logging.yaml_snapshot
  ├── NACOS-SENTINEL_GROUP/
  │   └── sentinel-rules.json_snapshot
  ├── NACOS-SEATA_GROUP/
  │   └── seata-config.yaml_snapshot
  └── NACOS-DEFAULT_GROUP/
      └── order-service.yaml_snapshot
```

**本地快照的写入时机：**

```java
// 每次成功从 Nacos Server 获取配置后，立即写入本地快照
public String getConfigFromServer(String dataId, String group, String tenant) {
    String content = httpGet("/nacos/v1/cs/configs", params);
    
    if (content != null) {
        // 写入本地快照（异步或同步）
        LocalConfigInfoProcessor.saveSnapshot(
            envName, dataId, group, tenant, content
        );
    }
    
    return content;
}

// 快照文件内容就是配置的原始字符串（未解析的 YAML/JSON/Properties）
```

**快照还支持容灾比对：**

```java
// ClientWorker 的检查逻辑（在长轮询之前先检查本地）
class LongPollingRunnable implements Runnable {
    @Override
    public void run() {
        // 阶段一：先检查本地文件是否有外部修改
        // （运维手动修改了快照文件的场景）
        List<String> changedLocalKeys = checkLocalConfig();
        for (String key : changedLocalKeys) {
            // 本地快照被外部修改 → 使用本地快照值
            // 这是一个手动容灾手段
            CacheData cache = cacheMap.get(key);
            cache.setContent(readLocalSnapshot(key));
            notifyListener(cache);
        }
        
        // 阶段二：再向 Server 发起长轮询
        List<String> changedKeys = checkUpdateDataIds(cacheKeys, 30000);
        // ...
    }
}
```

---

## 九、三层配置的典型使用场景和设计原则

### 设计原则

```
┌──────────────────────────────────────────────────────────┐
│                    配置分层设计原则                        │
│                                                          │
│  shared-configs: 不变性                                   │
│  ├── 存放所有服务共享的基础配置                             │
│  ├── 变更频率极低（DB连接信息、Redis地址等）                │
│  ├── 变更影响面大，需要灰度/蓝绿发布配合                    │
│  └── 建议 refresh: false（避免意外变更导致全集群故障）      │
│                                                          │
│  extension-configs: 可变性                                │
│  ├── 存放中间件和框架级配置                                │
│  ├── 变更频率中等（限流规则、熔断策略等）                    │
│  ├── 变更影响面可控，Dashboard 可视化管理                   │
│  └── 建议 refresh: true（业务规则需要动态调整）             │
│                                                          │
│  app-config: 高变性                                       │
│  ├── 存放各服务独有的业务配置                               │
│  ├── 变更频率高（功能开关、业务参数等）                      │
│  ├── 变更影响面最小（只影响单个服务）                       │
│  └── 必须 refresh: true（业务配置需要热更新）               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 典型配置文件内容

```yaml
# ===== common-datasource.yaml (shared-configs) =====
spring:
  datasource:
    type: com.zaxxer.hikari.HikariDataSource
    driver-class-name: com.mysql.cj.jdbc.Driver
    hikari:
      minimum-idle: 5
      maximum-pool-size: 20
      idle-timeout: 600000
      max-lifetime: 1800000
      connection-timeout: 30000
      connection-test-query: SELECT 1

# ===== common-redis.yaml (shared-configs) =====
spring:
  data:
    redis:
      host: redis-master.middleware
      port: 6379
      timeout: 3000
      lettuce:
        pool:
          max-active: 16
          max-idle: 8
          min-idle: 2
          max-wait: 3000

# ===== common-logging.yaml (shared-configs) =====
logging:
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n"
  level:
    root: INFO
    com.example: DEBUG
    org.springframework: WARN

# ===== sentinel-rules.json (extension-configs) =====
[
  {
    "resource": "/api/order/create",
    "limitApp": "default",
    "grade": 1,
    "count": 100,
    "strategy": 0,
    "controlBehavior": 0,
    "clusterMode": false
  },
  {
    "resource": "/api/order/query",
    "limitApp": "default",
    "grade": 0,
    "count": 200,
    "strategy": 0,
    "controlBehavior": 2,
    "maxQueueingTimeMs": 500
  }
]

# ===== seata-config.yaml (extension-configs) =====
seata:
  enabled: true
  application-id: ${spring.application.name}
  tx-service-group: my_tx_group
  service:
    vgroup-mapping:
      my_tx_group: default
    grouplist:
      default: seata-server.middleware:8091
  config:
    type: nacos
    nacos:
      server-addr: ${spring.cloud.nacos.config.server-addr}
      group: SEATA_GROUP
      namespace: ${spring.cloud.nacos.config.namespace}

# ===== order-service.yaml (app-config) =====
server:
  port: 8080
spring:
  datasource:
    url: jdbc:mysql://db-master:3306/order_db?useUnicode=true&characterEncoding=utf8&useSSL=true
    username: ENC(encrypted_order_user)
    password: ENC(encrypted_order_password)
  shardingsphere:
    datasource:
      names: ds0,ds1
order:
  max-items-per-page: 50
  default-timeout-seconds: 30
  feature:
    enable-new-checkout: true
    promotion-code-enabled: false
```

---

## 十、Namespace + Group + DataId 的三维模型

```
Nacos 配置的完整寻址：Namespace + Group + DataId

┌─────────────────────────────────────────────────────────────┐
│ Nacos Server                                                 │
│                                                              │
│  ┌─── Namespace: development ────────────────────────────┐  │
│  │                                                       │  │
│  │  Group: DEFAULT_GROUP                                │  │
│  │  ├── order-service.yaml                              │  │
│  │  ├── user-service.yaml                               │  │
│  │  └── gateway.yaml                                    │  │
│  │                                                       │  │
│  │  Group: SHARED_GROUP                                 │  │
│  │  ├── common-datasource.yaml                          │  │
│  │  ├── common-redis.yaml                               │  │
│  │  └── common-logging.yaml                             │  │
│  │                                                       │  │
│  │  Group: SENTINEL_GROUP                               │  │
│  │  └── sentinel-rules.json                             │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── Namespace: production ─────────────────────────────┐  │
│  │                                                       │  │
│  │  Group: DEFAULT_GROUP                                │  │
│  │  ├── order-service.yaml                              │  │
│  │  ├── user-service.yaml                               │  │
│  │  └── gateway.yaml                                    │  │
│  │                                                       │  │
│  │  Group: SHARED_GROUP                                 │  │
│  │  ├── common-datasource.yaml                          │  │
│  │  ├── common-redis.yaml                               │  │
│  │  └── common-logging.yaml                             │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

寻址公式：namespace（隔离环境）+ group（分类管理）+ dataId（唯一标识）

HTTP 请求时：
  GET /nacos/v1/cs/configs
  ? dataId=order-service.yaml
  & group=DEFAULT_GROUP
  & tenant=production-namespace-id        ← tenant 就是 namespace

namespace 的底层实现：
  Nacos Server 用 tenant_id 字段区分不同 namespace
  不同 namespace 的配置完全隔离，互不可见
  适合：开发/测试/生产 环境隔离

group 的底层实现：
  同一 namespace 内用 group_id 区分
  适合：shared / extension / sentinel 等分类管理

dataId 的底层实现：
  同一 group 内用 data_id 区分
  是配置的最小粒度单元
```

**不同 Namespace 的配置互不干扰：**

```java
// 开发环境和生产环境使用不同的 namespace
// 相同的 dataId = "order-service.yaml"
// 但 tenant 不同，所以内容完全独立

// 开发环境：
// namespace: development
// order-service.yaml:
//   spring.datasource.url: jdbc:mysql://dev-db:3306/order_db
//   server.port: 8080
//   logging.level.root: DEBUG

// 生产环境：
// namespace: production
// order-service.yaml:
//   spring.datasource.url: jdbc:mysql://prod-db:3306/order_db
//   server.port: 8080
//   logging.level.root: WARN
```

---

## 十一、Nacos 配置变更传播的完整链路

从运维在 Nacos Dashboard 修改一个配置值，到应用生效，经历了什么：

```
运维在 Nacos Dashboard 修改配置
  common-datasource.yaml 中 spring.datasource.hikari.maximum-pool-size: 20 → 50
      │
      ▼
┌─── Nacos Server 侧 ────────────────────────────────────┐
│                                                         │
│  1. 更新 config_info 表                                 │
│     UPDATE config_info                                  │
│     SET content = '...', md5 = '...', gmt_modified = NOW() |
│     WHERE data_id = 'common-datasource.yaml'            │
│       AND group_id = 'SHARED_GROUP'                     │
│       AND tenant_id = 'production'                      │
│                                                         │
│  2. 插入历史记录 his_config_info                         │
│     INSERT INTO his_config_info(...)                    │
│                                                         │
│  3. 内部通知机制                                        │
│     Nacos Server 内部维护一个 DataChangeNotifier         │
│     将变更的 dataId + group + tenant 加入通知队列        │
│                                                         │
│  4. 遍历所有订阅者，执行通知                             │
│     ├── 方式一：UDP Push                                │
│     │   查找订阅了该 dataId+group 的所有客户端           │
│     │   向每个客户端的 UDP 端口发送变更通知               │
│     │   通知内容：{"type":"notify","data":"dataId%02group"}│
│     │                                                  │
│     └── 方式二：Long Polling 响应                       │
│         该客户端之前发起的长轮询请求还 hold 着            │
│         立即返回 HTTP 200，body 包含变更的 dataId 列表   │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─── 应用侧（ClientWorker）──────────────────────────────┐
│                                                         │
│  5. 长轮询收到变更通知                                   │
│     changedDataIds = ["common-datasource.yaml"]         │
│                                                         │
│  6. 拉取最新配置                                        │
│     newContent = configService.getConfig(               │
│         "common-datasource.yaml",                       │
│         "SHARED_GROUP",                                 │
│         3000                                            │
│     );                                                  │
│     // newContent = "spring:\n  datasource:\n    hikari:│
│     //                   maximum-pool-size: 50"         │
│                                                         │
│  7. 更新本地缓存                                        │
│     CacheData cache = cacheMap.get(key);                │
│     cache.setContent(newContent);                       │
│     cache.setMd5(MD5Utils.md5Hex(newContent));          │
│                                                         │
│  8. 写入本地快照                                        │
│     LocalConfigInfoProcessor.saveSnapshot(              │
│         ..., newContent                                 │
│     );                                                  │
│                                                         │
│  9. 通知所有注册的 Listener                             │
│     for (Listener listener : cache.getListeners()) {    │
│         listener.receiveConfigInfo(newContent);         │
│     }                                                   │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─── Spring 生态响应 ────────────────────────────────────┐
│                                                         │
│  10. NacosPropertySource 更新                           │
│      找到 NacosPropertySource("common-datasource.yaml") │
│      更新其内部的 Properties                            │
│      "spring.datasource.hikari.maximum-pool-size" = 50 │
│                                                         │
│  11. 发布 EnvironmentChangeEvent                        │
│      Set<String> changedKeys = diff(oldEnv, newEnv);    │
│      // changedKeys = {"spring.datasource.hikari.       │
│      //                  maximum-pool-size"}            │
│      applicationContext.publishEvent(                   │
│          new EnvironmentChangeEvent(changedKeys)        │
│      );                                                 │
│                                                         │
│  12. ConfigurationPropertiesRebinder 处理               │
│      @ConfigurationProperties(prefix="spring.datasource")│
│      DataSourceProperties bean 被重新绑定               │
│                                                         │
│  13. RefreshScope Bean 销毁重建                         │
│      @RefreshScope 的 DataSource bean 被销毁            │
│      下次注入时重新创建（用新的 maximum-pool-size=50）    │
│                                                         │
│  14. HikariCP 连接池重建                                │
│      旧连接池 drain → 新连接池创建（max=50）             │
│      新连接逐渐建立到 50                                │
└─────────────────────────────────────────────────────────┘

总延迟：修改配置 → 应用生效 ≈ 1-3 秒
（取决于长轮询的响应时间和 Spring 刷新的速度）
```

---

## 总结

```
三层配置体系的本质：

shared-configs:
  → 最先加载，优先级最低（在 Nacos 层内）
  → 存放公共基础设施配置，变更需谨慎
  → 适合 refresh: false

extension-configs:
  → 中间加载，优先级中等
  → 存放中间件/框架配置，支持动态调整
  → 适合 refresh: true

app-config:
  → 最后加载，优先级最高（在 Nacos 层内）
  → 存放业务独有配置，高频变更
  → 必须 refresh: true

合并规则：同名 key，后加载的覆盖先加载的
查找顺序：先查优先级高的，找到即返回
降级策略：Nacos Server > 本地快照 > 跳过
刷新机制：refresh=true → 注册 Listener → 长轮询 → PropertySource 更新 → Bean 重建
```

三层配置的设计不是简单的文件分组，而是一套精心设计的 **优先级覆盖体系 + 故障降级体系 + 动态刷新体系**。理解了这些底层细节，才能在配置不生效、配置冲突、刷新失败等问题出现时快速定位根因。
