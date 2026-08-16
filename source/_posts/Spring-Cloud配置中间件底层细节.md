---
title: Spring Cloud 配置中间件底层细节
date: 2026-09-07 18:30:00
tags:
  - Spring Cloud
  - Config
  - Nacos
  - 微服务
categories:
  - 微服务
---

## 一、Spring Cloud 配置加载的底层机制

### 1. Bootstrap 上下文（引导上下文）

Spring Cloud 应用启动时，并非直接创建主 `ApplicationContext`，而是先创建一个 **Bootstrap Context**：

```
SpringApplication.run() 调用
      │
      ▼
┌─────────────────────────────────────────────────┐
│ 阶段一：创建 Bootstrap ApplicationContext       │
│                                                  │
│ 1. 加载 META-INF/spring.factories               │
│    org.springframework.cloud.bootstrap.          │
│    BootstrapConfiguration=...\                   │
│                                                  │
│ 2. 创建 PropertySourceLocator 实现               │
│    ├── NacosPropertySourceLocator               │
│    ├── ConfigServerPropertySourceLocator        │
│    └── ConsulPropertySourceLocator              │
│                                                  │
│ 3. 从远程配置中心拉取配置 → 注入 PropertySource  │
│                                                  │
│ 4. Bootstrap Context 中的 PropertySource        │
│    优先级高于本地 application.yml                 │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│ 阶段二：创建主 ApplicationContext                │
│                                                  │
│ 1. 合并 Bootstrap Context 的 PropertySource     │
│ 2. 加载 application.yml / application.properties │
│ 3. 注册 AutoConfiguration                       │
│ 4. 创建所有 Bean                                │
└─────────────────────────────────────────────────┘
```

**底层源码调用链：**

```java
// SpringApplication.run() 内部
public ConfigurableApplicationContext run(String... args) {
    // ...
    // 关键：在 prepareContext 阶段判断是否需要 Bootstrap
    ConfigurableApplicationContext context = null;
    
    // Spring Cloud 通过 ApplicationContextInitializer 注入
    // BootstrapApplicationListener 监听 ApplicationEnvironmentPreparedEvent
    // 发现需要 Bootstrap 时，提前创建子上下文

    // BootstrapApplicationListener.onApplicationEvent() 核心逻辑：
    ConfigurableApplicationContext bootstrapContext = 
        bootstrapServiceLocator.locate(
            bootstrapContext(environment)
        );
    
    // Bootstrap 配置源的优先级
    // compositePropertySources 包含从 Nacos/Consul/ConfigServer 拉取的所有配置
    // 这些配置源插入到 Environment 的 PropertySources 列表最前面
    environment.getPropertySources().addFirst(bootstrapPropertySource);
}
```

### 2. PropertySource 优先级体系

```
优先级从高到低：

┌────────────────────────────────────────────────────┐
│ ① 命令行参数 (--server.port=9090)                  │  最高
├────────────────────────────────────────────────────┤
│ ② Nacos 共享配置 shared-configs                    │
├────────────────────────────────────────────────────┤
│ ③ Nacos 扩展配置 extension-configs                 │
├────────────────────────────────────────────────────┤
│ ④ Nacos 应用专属配置 (dataId=order-service.yaml)   │
├────────────────────────────────────────────────────┤
│ ⑤ JVM 系统属性 (-Dserver.port=8080)                │
├────────────────────────────────────────────────────┤
│ ⑥ 操作系统环境变量 (SERVER_PORT=8080)              │
├────────────────────────────────────────────────────┤
│ ⑦ application-{profile}.yml                       │
├────────────────────────────────────────────────────┤
│ ⑧ application.yml                                 │
├────────────────────────────────────────────────────┤
│ ⑨ bootstrap.yml                                   │
├────────────────────────────────────────────────────┤
│ ⑩ @PropertySource 注解指定的配置                   │  最低
└────────────────────────────────────────────────────┘

Spring 用 CompositePropertySource 管理所有配置源
查询时从上到下逐层查找，找到即返回
```

**源码层面的优先级实现：**

```java
// Spring Environment 的 propertySources 结构
MutablePropertySources propertySources = environment.getPropertySources();

// 实际顺序（调试时可看到）：
// 0. commandLineArgs                          ← 最先查找
// 1. nacosPropertySource_group1
// 2. nacosPropertySource_group2
// 3. nacosPropertySource_extension1
// 4. systemProperties
// 5. systemEnvironment
// 6. applicationConfig: [classpath:/application-prod.yml]
// 7. applicationConfig: [classpath:/application.yml]
// 8. defaultProperties

// 查找逻辑：
public <T> T getProperty(String key, Class<T> targetClass) {
    // 遍历 propertySources，从 index 0 开始
    for (PropertySource<?> source : this.propertySources) {
        Object value = source.getProperty(key);
        if (value != null) {
            return convert(value, targetClass);  // 找到立即返回
        }
    }
    return null;  // 所有源都没找到
}
```

---

## 二、Nacos Config 底层机制

### 1. 配置拉取流程

```java
// NacosPropertySourceLocator.locate() 是入口
public class NacosPropertySourceLocator implements PropertySourceLocator {
    
    @Override
    public PropertySource<?> locate(Environment env) {
        // 1. 构建 NacosConfigProperties
        NacosConfigProperties properties = nacosConfigPropertiesBuilder.build(env);
        
        // 2. 创建 NacosConfigService（核心客户端）
        ConfigService configService = nacosConfigServiceBuilder.build(properties);
        
        // 3. 加载共享配置
        List<NacosConfigProperties.Config> sharedConfigs = properties.getSharedConfigs();
        for (Config shared : sharedConfigs) {
            // 调用 Nacos Server 的 HTTP 接口拉取配置
            String config = configService.getConfig(
                shared.getDataId(),     // 如 "common-datasource.yaml"
                shared.getGroup(),      // 如 "SHARED_GROUP"
                timeout
            );
            // 解析为 PropertySource 并缓存
            composite.addPropertySource(buildPropertySource(config, shared));
        }
        
        // 4. 加载扩展配置
        // ... 同上
        
        // 5. 加载应用专属配置
        String dataId = properties.getName() + "." + properties.getFileExtension();
        // 如 "order-service.yaml"
        String appConfig = configService.getConfig(
            dataId, 
            properties.getGroup(),   // 如 "DEFAULT_GROUP"
            timeout
        );
        composite.addPropertySource(buildPropertySource(appConfig));
        
        return composite;
    }
}
```

**NacosConfigService.getConfig() 的底层实现：**

```java
// ConfigService 的内部实现
public class NacosConfigService implements ConfigService {
    
    private final ServerListManager serverListManager;  // 管理 Nacos Server 列表
    private final ClientWorker clientWorker;            // 负责长轮询
    
    @Override
    public String getConfig(String dataId, String group, long timeout) 
            throws NacosException {
        return getConfigInner(namespace, dataId, group, timeout);
    }
    
    private String getConfigInner(String tenant, String dataId, String group, 
                                   long timeout) throws NacosException {
        // ========== 第一步：查本地快照 ==========
        // 先从本地文件缓存读取（断线恢复场景）
        String content = LocalConfigInfoProcessor.getFailover(
            agent.getName(), dataId, group, tenant
        );
        if (content != null) {
            return content;
        }
        
        // ========== 第二步：向 Nacos Server 发起 HTTP 请求 ==========
        // GET /nacos/v1/cs/configs
        // 参数: dataId, group, tenant, timeout
        content = worker.getServerConfig(dataId, group, tenant, timeout);
        
        // ========== 第三步：写入本地快照 ==========
        LocalConfigInfoProcessor.saveSnapshot(
            agent.getName(), dataId, group, tenant, content
        );
        
        return content;
    }
}
```

**HTTP 请求的完整 URL：**

```
GET http://nacos-server:8848/nacos/v1/cs/configs?
    dataId=order-service.yaml
    &group=DEFAULT_GROUP
    &tenant=production-namespace-id
    &timeout=30000

Headers:
    accessToken: eyJhbGciOiJIUzI1NiJ9...
    Long-Polling-Timeout: 30000
    Client-AppName: unknown
```

### 2. 配置变更监听（长轮询机制）

```
应用启动后，后台线程持续监听配置变更：

┌──────────────┐                    ┌──────────────┐
│  应用 Pod     │                    │ Nacos Server │
│              │                    │              │
│ ClientWorker │──HTTP GET──────────→│              │
│ (长轮询)      │  /listener         │ hold 住连接  │
│              │  headers:           │ 30秒不响应   │
│              │  Long-Polling-     │              │
│              │  Timeout: 30000    │              │
│              │                    │              │
│              │                    │ 配置变更！    │
│              │←──200 OK───────────│ 立即返回      │
│              │  body:             │ 变更的        │
│              │  changedDataIds    │ dataId 列表   │
│              │                    │              │
│              │──GET /configs──────→│ 拉取新配置    │
│              │←──200 OK───────────│ 返回新内容    │
│              │                    │              │
│              │  更新内存中的         │              │
│              │  PropertySource    │              │
│              │  触发 RefreshEvent │              │
│              │                    │              │
│              │──HTTP GET──────────→│ 新一轮长轮询  │
│              │  (重新发起)          │              │
└──────────────┘                    └──────────────┘

如果 30 秒内没有配置变更：
  Nacos Server 返回 200 + 空 body
  ClientWorker 立即重新发起下一轮长轮询
```

**ClientWorker 长轮询的核心源码：**

```java
class ClientWorker {
    
    // 线程池：用于长轮询
    private final ScheduledExecutorService executor;
    // 线程池：用于配置变更后的拉取
    private final ExecutorService notifyExecutor;
    
    // 每个 namespace 一个 LongPollingRunnable
    class LongPollingRunnable implements Runnable {
        
        private List<String> cacheDataKeys;  // 当前负责检查的配置列表
        
        @Override
        public void run() {
            try {
                // ========== 阶段一：检查本地配置是否变更 ==========
                List<String> changedGroupKeys = checkLocalConfig();
                
                // ========== 阶段二：向 Server 发起长轮询 ==========
                // POST /nacos/v1/cs/configs/listener
                // Body: Listening-Configs=dataId1%02group1%02md51%01dataId2%02group2%02md52
                List<String> changedKeys = checkUpdateDataIds(
                    cacheDataKeys, 
                    30000  // 长轮询超时
                );
                
                // ========== 阶段三：拉取变更的配置 ==========
                for (String changedKey : changedKeys) {
                    String[] parts = parseKey(changedKey);
                    String dataId = parts[0];
                    String group = parts[1];
                    
                    // 从 Server 拉取最新内容
                    String content = getServerConfig(dataId, group, tenant, 3000);
                    
                    // 更新本地缓存
                    CacheData cache = cacheMap.get(GroupKey.getKeyTenant(dataId, group, tenant));
                    cache.setContent(content);
                    cache.setMd5(MD5Utils.md5Hex(content));
                    
                    // 通知监听器（触发 @RefreshScope 刷新）
                    notifyListener(cache);
                }
                
            } catch (Exception e) {
                // 异常时延迟重试
                executor.schedule(this, 15, TimeUnit.SECONDS);
                return;
            }
            
            // 继续下一轮长轮询
            executor.execute(this);
        }
    }
}
```

### 3. 配置变更通知到 Spring Bean 的完整链路

```
Nacos Server 推送配置变更
      │
      ▼
ClientWorker 长轮询收到变更通知
      │
      ▼
拉取最新配置内容，更新 CacheData
      │
      ▼
CacheData 的 Listener 被触发
      │
      ▼
NacosContextRefresher.onApplicationEvent()
      │
      ▼
发布 RefreshEvent 到 Spring ApplicationContext
      │
      ▼
RefreshEventListener.onApplicationEvent()
      │
      ▼
ContextRefresher.refresh()
      │
      ├──→ 重新构建 Environment（拉取最新 PropertySource）
      │
      ├──→ 比较新旧 Environment，找出变更的 key
      │
      └──→ 发布 EnvironmentChangeEvent
              │
              ▼
     @RefreshScope 标注的 Bean 被销毁并重建
     @ConfigurationProperties 标注的 Bean 重新绑定属性
     @Value 注入的属性会在下次访问时获取新值
```

**@RefreshScope 的底层实现：**

```java
// @RefreshScope 本质是 @Scope("refresh")
// Spring 为它注册了自定义的 Scope 实现

public class RefreshScope extends GenericScope 
        implements ApplicationContextAware, BeanDefinitionRegistryPostProcessor {
    
    // 所有 refresh scope 的 Bean 存储在 StandardCache 中
    // Bean 实际上是代理对象
    
    // 当收到 RefreshEvent 时：
    public void refreshAll() {
        // 销毁所有 refresh scope 的 Bean
        super.destroy();
        // 下次注入时会重新创建（懒加载）
    }
    
    // 当某个 key 变化时：
    public void refresh(String name) {
        // 只销毁指定的 Bean
        super.destroy(name);
    }
}

// @RefreshScope Bean 的实际创建过程：
// 1. Spring 不直接创建目标 Bean
// 2. 而是创建一个 ScopedProxyFactoryBean 作为代理
// 3. 每次方法调用时，代理从 Scope 缓存中获取真实 Bean
// 4. refresh() 后缓存被清除，下次调用会重建 Bean

// 代理对象的调用链：
proxy.getUserById()
  → RefreshScope.get("userConfig")    // 查缓存
    → 缓存命中：返回已有的 Bean
    → 缓存未命中：重新创建 Bean（用最新的配置值注入）
```

### 4. Nacos 配置的数据模型与存储

```
Nacos Server 侧的数据模型：

┌─────────────────────────────────────────────┐
│  Namespace（命名空间）                        │
│  ID: production-namespace-id                 │
│  ┌───────────────────────────────────────┐  │
│  │  Group: DEFAULT_GROUP                 │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  DataId: order-service.yaml     │  │  │
│  │  │  Content:                       │  │  │
│  │  │    server:                       │  │  │
│  │  │      port: 8080                  │  │  │
│  │  │    spring:                       │  │  │
│  │  │      datasource:                 │  │  │
│  │  │        url: jdbc:mysql://...     │  │  │
│  │  │  Type: yaml                      │  │  │
│  │  │  MD5: a1b2c3d4e5f6...            │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  DataId: user-service.yaml      │  │  │
│  │  │  ...                            │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │  Group: SHARED_GROUP                  │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  DataId: common-datasource.yaml │  │  │
│  │  │  ...                            │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**Nacos 服务端的配置存储结构（MySQL）：**

```sql
-- config_info 表（核心表）
CREATE TABLE config_info (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_id     VARCHAR(255) NOT NULL,    -- 配置文件名
    group_id    VARCHAR(128) NOT NULL,    -- 分组
    tenant_id   VARCHAR(128) DEFAULT '',  -- 命名空间 ID
    content     LONGTEXT NOT NULL,        -- 配置内容
    md5         VARCHAR(32) NOT NULL,     -- 内容 MD5
    gmt_create  DATETIME NOT NULL,
    gmt_modified DATETIME NOT NULL,
    src_user    TEXT,
    src_ip      VARCHAR(50),
    app_name    VARCHAR(128),
    type        VARCHAR(64),              -- yaml/properties/json
    encrypted_data_key TEXT NOT NULL       -- 加密密钥（AES）
);

-- his_config_info 表（历史版本，用于回滚）
CREATE TABLE his_config_info (
    id         BIGINT,
    nid        BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_id    VARCHAR(255) NOT NULL,
    group_id   VARCHAR(128) NOT NULL,
    tenant_id  VARCHAR(128) DEFAULT '',
    content    LONGTEXT NOT NULL,
    md5        VARCHAR(32),
    gmt_create DATETIME NOT NULL,
    gmt_modified DATETIME NOT NULL,
    src_user   TEXT,
    src_ip     VARCHAR(50),
    op_type    CHAR(10)     -- I=插入 U=更新 D=删除
);

-- config_tags_relation 表（标签关联）
-- group_capacity 表（分组容量限制）
-- tenant_capacity 表（命名空间容量限制）
-- tenant_info 表（命名空间信息）
```

### 5. Nacos 配置加密

```
Nacos 2.1+ 支持配置加密（AES-CBC）：

客户端加密写入：
  原始配置: db.password=p@ssw0rd123
      │
      ▼  客户端使用 AES 密钥加密
  加密后: db.password=ENC(ciphertext_base64_encoded)
      │
      ▼  写入 Nacos Server
  存储: content="db.password=ENC(ciphertext...)"
  encrypted_data_key: 加密的 AES 密钥（用 KMS 保护）

客户端读取解密：
  从 Server 获取加密内容
      │
      ▼
  识别 ENC(...) 标记
      │
      ▼
  用 AES 密钥解密
      │
      ▼
  返回明文给应用: db.password=p@ssw0rd123
```

---

## 三、Nacos Discovery 底层机制

### 1. 服务注册的完整流程

```java
// 应用启动时的注册链路

// 入口：@EnableDiscoveryClient + spring-cloud-starter-alibaba-nacos-discovery
// 通过 AutoConfiguration 自动装配

// NacosDiscoveryAutoConfiguration 注册了：
// 1. NacosServiceRegistry        → 实现 ServiceRegistry 接口
// 2. NacosRegistration           → 封装注册信息
// 3. NacosAutoServiceRegistration → 监听 WebServerInitializedEvent

// 当 Web 服务器启动完成后：
@EventListener(WebServerInitializedEvent.class)
public void onApplicationEvent(WebServerInitializedEvent event) {
    registration.setPort(event.getWebServer().getPort());
    serviceRegistry.register(registration);
}
```

**NacosServiceRegistry.register() 底层：**

```java
public class NacosServiceRegistry implements ServiceRegistry<Registration> {
    
    @Override
    public void register(Registration registration) {
        // 1. 构建 Instance 对象
        Instance instance = new Instance();
        instance.setIp(registration.getHost());       // Pod IP
        instance.setPort(registration.getPort());      // 8080
        instance.setWeight(nacosDiscoveryProperties.getWeight());
        instance.setClusterName(nacosDiscoveryProperties.getClusterName());
        instance.setMetadata(registration.getMetadata());
        // 元数据包括：preserved.register.source=SPRING_CLOUD 等
        
        // 2. 调用 NamingService.registerInstance()
        namingService.registerInstance(
            registration.getServiceId(),  // "order-service"
            instance
        );
    }
}

// NamingProxy.registerService() 底层 HTTP 请求：
// POST http://nacos-server:8848/nacos/v1/ns/instance
// 参数:
//   ip=10.244.1.5
//   port=8080
//   weight=1.0
//   enabled=true
//   healthy=true
//   metadata={"preserved.register.source":"SPRING_CLOUD"}
//   serviceName=order-service
//   groupName=DEFAULT_GROUP
//   namespaceId=production-namespace-id
//   clusterName=DEFAULT
```

### 2. 心跳维持的底层

```java
// 注册成功后，后台线程持续发送心跳

class BeatReactor implements Runnable {
    
    // 心跳任务调度表
    private final ScheduledExecutorService executor;
    private final ConcurrentMap<String, BeatInfo> dom2Beat = new ConcurrentHashMap<>();
    
    // 添加心跳任务
    public void addBeatInfo(String serviceName, BeatInfo beatInfo) {
        dom2Beat.put(buildKey(serviceName, beatInfo.getIp(), beatInfo.getPort()), beatInfo);
        // 每 5 秒发送一次心跳
        executor.schedule(new BeatTask(beatInfo), 0, TimeUnit.MILLISECONDS);
    }
    
    class BeatTask implements Runnable {
        @Override
        public void run() {
            try {
                // PUT /nacos/v1/ns/instance/beat
                // 参数: serviceName, ip, port, clusterName
                long nextTime = sendBeat(beatInfo);
                // 根据服务端返回的心跳间隔调度下次心跳
                executor.schedule(this, nextTime, TimeUnit.MILLISECONDS);
            } catch (NacosException e) {
                // 心跳失败，增加重试间隔
                long nextTime = beatInfo.getPeriod() * 2;
                executor.schedule(this, nextTime, TimeUnit.MILLISECONDS);
            }
        }
    }
}

// Nacos Server 收到心跳后：
// 1. 更新该实例的 lastBeat 时间戳
// 2. 如果实例之前标记为不健康，恢复为健康
// 3. 返回心跳间隔（默认 5000ms）

// Nacos Server 的健康检查：
// 如果超过 15 秒没有收到心跳 → 标记实例为不健康（unhealthy）
// 如果超过 30 秒没有收到心跳 → 从注册列表中删除实例
```

### 3. 服务发现的底层

```java
// 服务发现的两种模式

// 模式一：Pull（拉模式）
// 客户端主动查询实例列表
public List<Instance> getAllInstances(String serviceName) {
    // 先查本地缓存
    ServiceInfo serviceInfo = serviceInfoMap.get(serviceName);
    if (serviceInfo != null) {
        return serviceInfo.getHosts();
    }
    // 缓存没有，从 Server 拉取
    // GET /nacos/v1/ns/instance/list
    // 参数: serviceName, groupName, namespaceId, clusters
    String result = reqAPI("/ns/instance/list", params);
    serviceInfo = JSON.parseObject(result, ServiceInfo.class);
    serviceInfoMap.put(serviceName, serviceInfo);
    return serviceInfo.getHosts();
}

// 模式二：Push（推模式，UDP）
// Nacos Server 主动推送变更
class PushReceiver implements Runnable {
    @Override
    public void run() {
        // 监听 UDP 端口
        DatagramSocket socket = new DatagramSocket(0);  // 随机端口
        // 将 UDP 端口告诉 Server（注册时携带）
        
        while (running) {
            byte[] buffer = new byte[65535];
            DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
            socket.receive(packet);  // 阻塞等待
            
            // 解析推送数据
            String json = new String(packet.getData(), 0, packet.getLength(), "UTF-8");
            PushPacket pushPacket = JSON.parseObject(json, PushPacket.class);
            
            if (PushPacket.NOTIFY.equals(pushPacket.type)) {
                // 收到服务变更通知
                String serviceKey = pushPacket.data;
                // 重新从 Server 拉取最新实例列表
                ServiceInfo info = getServiceInfo(serviceKey);
                serviceInfoMap.put(serviceKey, info);
                // 通知 Listener
                NotifyCenter.publishEvent(new ServiceChangeEvent(info));
            }
        }
    }
}

// 模式三：Long Polling（兜底）
// 和配置中心一样，每 30 秒一次长轮询
// 确保即使 UDP 推送丢失也能发现变更
```

### 4. 服务发现与 Ribbon/LoadBalancer 的集成

```
Feign 调用链路：

@FeignClient("user-service")
interface UserClient {
    @GetMapping("/api/user/{id}")
    UserDTO getUser(@PathVariable Long id);
}

userClient.getUser(1L)
      │
      ▼
FeignInvocationHandler.invoke()
      │
      ▼
SynchronousMethodHandler.executeAndDecode()
      │
      ▼
LoadBalancerFeignClient.execute()
      │
      ▼
FeignBlockingLoadBalancerClient.execute()
      │
      ▼
ReactorLoadBalancer<ServiceInstance>.choose()  // 负载均衡选择实例
      │
      ├──→ 从 NacosDiscoveryClient.getInstances("user-service") 获取实例列表
      │    返回: [10.244.2.8:8080, 10.244.2.9:8080, 10.244.3.5:8080]
      │
      ├──→ 应用负载均衡策略
      │    ├── RoundRobin（轮询，默认）
      │    ├── Random（随机）
      │    ├── WeightedResponseTime（响应时间加权）
      │    └── 自定义（如 ZoneAvoidanceRule）
      │
      └──→ 选中: 10.244.2.8:8080
              │
              ▼
        构造 HTTP 请求 → 发送到选中的实例
```

**Spring Cloud LoadBalancer 的核心接口：**

```java
// 负载均衡器
public interface ReactorServiceInstanceLoadBalancer {
    Mono<Response<ServiceInstance>> choose(Request request);
}

// RoundRobin 实现
public class RoundRobinLoadBalancer implements ReactorServiceInstanceLoadBalancer {
    
    private final AtomicInteger position = new AtomicInteger(
        ThreadLocalRandom.current().nextInt(1000)
    );
    
    @Override
    public Mono<Response<ServiceInstance>> choose(Request request) {
        // 从 ServiceInstanceListSupplier 获取实例列表
        return supplier.get(request)
            .next()
            .map(instances -> {
                if (instances.isEmpty()) {
                    return new EmptyResponse();
                }
                // 轮询算法：取模
                int pos = Math.abs(this.position.incrementAndGet());
                ServiceInstance instance = instances.get(pos % instances.size());
                return new DefaultResponse(instance);
            });
    }
}
```

---

## 四、Sentinel 底层配置机制

### 1. 规则定义与存储

```java
// Sentinel 的规则体系
// 每种规则对应一个 RuleManager

// 限流规则
public class FlowRule extends AbstractRule {
    private String resource;           // 资源名
    private int grade;                 // QPS(0) 或 THREAD(1)
    private double count;              // 限流阈值
    private int controlBehavior;       // 直接拒绝(0) / WarmUp(1) / 排队等待(2)
    private int warmUpPeriodSec;       // 预热时长
    private int maxQueueingTimeMs;     // 排队等待超时
}

// 规则存储位置（可切换）
// 1. 内存（默认）
// 2. 文件持久化
// 3. Nacos（推荐生产环境）
// 4. ZooKeeper
// 5. Apollo
```

### 2. Sentinel 与 Nacos 规则持久化的底层

```java
// Sentinel 从 Nacos 拉取规则的实现

// 自定义 Nacos 数据源
@Bean
public DataSource<List<FlowRule>> flowRuleDataSource() {
    // Nacos 数据源
    return new NacosDataSource<>(
        nacosProperties,         // Nacos 连接信息
        groupId,                 // "SENTINEL_GROUP"
        dataId,                  // "order-service-flow-rules"
        // 规则解析器：JSON → List<FlowRule>
        new Converter<String, List<FlowRule>>() {
            @Override
            public List<FlowRule> convert(String source) {
                return JSON.parseArray(source, FlowRule.class);
            }
        }
    );
}

// NacosDataSource 的内部结构：
public class NacosDataSource<T> extends AbstractDataSource<String, T> {
    
    private ConfigService configService;
    private ExecutorService executor;
    
    // 初始化时：拉取配置 + 注册监听
    @PostConstruct
    public void init() {
        // 1. 首次拉取规则
        String config = configService.getConfig(dataId, groupId, timeout);
        T rules = converter.convert(config);
        // 注册到 Sentinel 的 RuleManager
        property.update(rules);
        
        // 2. 注册 Nacos 监听器（配置变更时自动更新）
        configService.addListener(dataId, groupId, new Listener() {
            @Override
            public void receiveConfigInfo(String configInfo) {
                // 配置变更 → 解析新规则 → 更新 Sentinel
                T newRules = converter.convert(configInfo);
                property.update(newRules);
            }
        });
    }
}
```

**Sentinel Dashboard 推送规则到 Nacos 的流程：**

```
Dashboard 界面修改规则
      │
      ▼
Dashboard 后端调用 Nacos Open API
  POST /nacos/v1/cs/configs
  dataId: order-service-flow-rules
  group: SENTINEL_GROUP
  content: [
    {
      "resource": "/api/order/create",
      "grade": 1,
      "count": 100,
      "controlBehavior": 0
    }
  ]
      │
      ▼
Nacos Server 存储配置并通知订阅者
      │
      ▼
各服务实例的 NacosDataSource Listener 收到通知
      │
      ▼
解析 JSON → FlowRule 对象 → FlowRuleManager.loadRules()
      │
      ▼
Sentinel 生效新规则
```

### 3. Sentinel 限流判断的底层实现

```java
// 一次请求通过 Sentinel 限流器的完整调用链

Entry entry = SphU.entry("/api/order/create");
try {
    // 业务逻辑
} finally {
    entry.exit();
}

// SphU.entry() 内部：
public Entry entry(String resource, EntryType type, int count, Object... args) {
    // 1. 查找资源对应的 ProcessorSlotChain
    ProcessorSlotChain chain = lookProcessChain(resource);
    
    // 2. 执行责任链
    chain.entry(context, resourceWrapper, null, count, args);
}

// ProcessorSlotChain 的执行顺序：
// NodeSelectorSlot → ClusterBuilderSlot → StatisticSlot
// → FlowSlot → DegradeSlot → SystemSlot → AuthoritySlot

// FlowSlot 中的限流判断：
public class FlowSlot extends AbstractLinkedProcessorSlot<DefaultNode> {
    @Override
    public void entry(Context context, ResourceWrapper resource, 
                      DefaultNode node, int count, Object... args) {
        // 调用 FlowRuleChecker
        checker.checkFlow(ruleProvider, resource, context, node, count, args);
    }
}

// FlowRuleChecker.checkFlow() 核心逻辑：
public void checkFlow(...) {
    // 1. 获取该资源的所有限流规则
    List<FlowRule> rules = flowRules.get(resource);
    
    for (FlowRule rule : rules) {
        // 2. 获取流量控制器
        TrafficController controller = selectController(rule, context, node);
        
        // 3. 判断是否允许通过
        boolean canPass = controller.canPass(context, node, count, args);
        
        if (!canPass) {
            // 触发限流 → 抛出 FlowException
            throw new FlowException(rule.getLimitApp(), rule);
        }
    }
}

// DefaultController（直接拒绝）的 canPass 实现：
public boolean canPass(Context context, DefaultNode node, int acquireCount, 
                       boolean prioritized) {
    // 获取当前统计窗口的 QPS 或线程数
    // 使用滑动窗口计数器（LeapArray）
    double curCount = avgUsedTokens(node);
    
    if (curCount + acquireCount > count) {
        // 超过阈值，拒绝
        return false;
    }
    // 未超过，放行
    return true;
}

// 滑动窗口计数器的实现（StatisticSlot 内部）：
// LeapArray 用一个环形数组存储多个时间窗口的统计
// 每个窗口大小 500ms，总共 20 个窗口 → 10 秒的数据

┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ W0   │ W1   │ W2   │ W3   │ W4   │ ...  │ W18  │ W19  │
│ 500ms│ 500ms│ 500ms│ 500ms│ 500ms│      │ 500ms│ 500ms│
│ QPS: │ QPS: │ QPS: │ QPS: │ QPS: │      │ QPS: │ QPS: │
│ 120  │ 95   │ 88   │ 102  │ 76   │      │ 90   │ 85   │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
                              ↑ 当前时间窗口
        总 QPS = 所有窗口请求数之和 / 总时长
```

---

## 五、Seata 分布式事务配置底层

### 1. Seata 的三个核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                     Seata 架构                              │
│                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                │
│  │ TM      │    │ RM      │    │ RM      │                │
│  │(事务管理器)│   │(资源管理器)│   │(资源管理器)│               │
│  │Order Svc│    │Order Svc│    │User Svc │                │
│  └────┬────┘    └────┬────┘    └────┬────┘                │
│       │              │              │                      │
│       │    注册/报告  │   注册/报告  │                      │
│       └──────────────┼──────────────┘                      │
│                      │                                     │
│                ┌─────▼──────┐                              │
│                │     TC     │                              │
│                │ (事务协调器) │                              │
│                │ Seata Server│                              │
│                └────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

### 2. Seata 代理数据源的底层

```java
// Seata 对 DataSource 的代理是核心机制

// 配置方式
@Configuration
public class DataSourceConfig {
    @Bean
    @Primary
    public DataSource dataSource(DataSourceProperties properties) {
        // 原始数据源
        DataSource raw = properties.initializeDataSourceBuilder().build();
        // 用 Seata 的 DataSourceProxy 包装
        return new DataSourceProxy(raw);
    }
}

// DataSourceProxy 的作用：
// 在 SQL 执行前后自动插入全局事务逻辑

public class DataSourceProxy extends AbstractDataSourceProxy {
    
    @Override
    public ConnectionProxy getConnection() throws SQLException {
        // 返回被代理的 Connection
        Connection target = targetDataSource.getConnection();
        return new ConnectionProxy(this, target);
    }
}

// ConnectionProxy 的核心：
public class ConnectionProxy extends AbstractConnectionProxy {
    
    @Override
    public PreparedStatement prepareStatement(String sql) throws SQLException {
        // 用 PreparedStatementProxy 包装
        return new PreparedStatementProxy(this, targetConnection.prepareStatement(sql));
    }
    
    @Override
    public void commit() throws SQLException {
        // 如果在全局事务中：
        if (context.inGlobalTransaction()) {
            // 不真正提交本地事务
            // 而是向 TC 注册分支事务 + 记录 undo_log
            doCommit();
        } else {
            targetConnection.commit();
        }
    }
}

// PreparedStatementProxy 执行 SQL 时：
public class PreparedStatementProxy extends AbstractPreparedStatementProxy {
    
    @Override
    public ResultSet executeQuery() throws SQLException {
        // 记录执行前的数据快照（before image）
        // 执行 SQL
        // 记录执行后的数据快照（after image）
        // 将 before/after image 存入 undo_log 表
        
        // AT 模式的核心：通过 before/after image 实现回滚
        TableRecords beforeImage = TableMetaCache.getTableMeta(dataSource)
            .buildBeforeImage(sql, parameters);
        
        ResultSet rs = targetPreparedStatement.executeQuery();
        
        TableRecords afterImage = TableMetaCache.getTableMeta(dataSource)
            .buildAfterImage(sql, parameters);
        
        // 生成 undo_log 记录
        SQLUndoLog undoLog = new SQLUndoLog(
            sqlType,       // INSERT/UPDATE/DELETE
            tableName,
            beforeImage,
            afterImage
        );
        context.addUndoItem(undoLog);
        
        return rs;
    }
}
```

### 3. AT 模式的 undo_log 机制

```sql
-- undo_log 表（每个业务库都需要创建）
CREATE TABLE undo_log (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    branch_id     BIGINT NOT NULL,       -- 分支事务 ID
    xid           VARCHAR(100) NOT NULL,  -- 全局事务 ID
    context       VARCHAR(128) NOT NULL,  -- 上下文信息
    rollback_info  LONGBLOB NOT NULL,     -- 回滚信息（序列化的 before/after image）
    log_status    INT NOT NULL DEFAULT 0, -- 0=正常 1=已回滚
    log_created   DATETIME NOT NULL,
    log_modified  DATETIME NOT NULL,
    ext           VARCHAR(100) DEFAULT NULL,
    UNIQUE KEY ux_undo_log (xid, branch_id)
);
```

**AT 模式执行流程：**

```
TM 开启全局事务（@GlobalTransactional）
      │
      ├──→ 向 TC 发起 begin 请求
      │    TC 返回全局事务 XID: "192.168.1.10:8091:123456789"
      │
      ▼
RM 执行本地 SQL（order 表 INSERT）
      │
      ├──→ DataSourceProxy 拦截 SQL
      │
      ├──→ 解析 SQL，获取操作的表和行
      │    解析结果: INSERT INTO order(id, user_id, amount) VALUES(1, 100, 99.9)
      │
      ├──→ 查询 before image（如果是 UPDATE/DELETE）
      │    SELECT id, user_id, amount FROM order WHERE id = 1 FOR UPDATE
      │    before: {id=1, user_id=100, amount=50.0}
      │
      ├──→ 执行原始 SQL
      │    INSERT INTO order(...) VALUES(...)
      │
      ├──→ 查询 after image
      │    SELECT id, user_id, amount FROM order WHERE id = 1
      │    after: {id=1, user_id=100, amount=99.9}
      │
      ├──→ 生成 undo_log，插入到 undo_log 表
      │    INSERT INTO undo_log(branch_id, xid, rollback_info, ...)
      │    rollback_info = JSON(beforeImage, afterImage, sqlType)
      │
      ├──→ 向 TC 注册分支事务
      │    TC 记录: XID=xxx, branchId=yyy, resourceId=orderDS, tableName=order
      │
      └──→ 本地事务提交（SQL + undo_log 在同一个本地事务中）

=== 如果需要回滚 ===

TC 通知 RM 回滚分支事务
      │
      ▼
RM 根据 undo_log 执行反向操作：
  INSERT → 生成 DELETE（根据 after image 的主键）
  UPDATE → 生成 UPDATE（恢复 before image 的值）
  DELETE → 生成 INSERT（根据 before image 的值）
      │
      ▼
删除 undo_log 记录
      │
      ▼
回滚完成
```

### 4. Seata 客户端连接 TC 的底层

```java
// Seata 客户端（TM/RM）与 TC（Server）的通信

// 使用 Netty 建立长连接
public class NettyClientChannelManager {
    
    // 连接池：每个应用维护到 TC 的 Netty 连接
    private final ConcurrentMap<String, Object> channelLocks = new ConcurrentHashMap<>();
    private final ConcurrentMap<String, NettyPoolKey.TransactionRole> clientChannels;
    
    // 获取到 TC 的连接
    public Channel borrowChannel(ServerAddress serverAddress) {
        // 从连接池获取已有连接
        // 如果没有，建立新的 Netty 连接
        return getPool(serverAddress).borrowObject();
    }
}

// RM 启动时：
// 1. 连接 TC Server（Netty 长连接）
// 2. 发送注册消息：
//    RM_REG: resourceId=orderDS, applicationId=order-service
// 3. TC 返回 RMID

// TM 开启全局事务时：
// 1. 发送 GLOBAL_BEGIN 请求
// 2. TC 返回 XID

// TC 通知 RM 回滚时：
// 1. 通过 Netty 长连接发送 BRANCH_ROLLBACK 消息
// 2. RM 收到后执行 undo_log 回滚逻辑
// 3. 返回 BRANCH_ROLLBACK_RESULT
```

---

## 六、OpenFeign 底层配置

### 1. Feign 的动态代理机制

```java
// @EnableFeignClients 启动时扫描所有 @FeignClient 接口

// FeignClientFactoryBean 是 FactoryBean
// 每个 @FeignClient 接口对应一个 FeignClientFactoryBean

// 当注入 UserClient 时，FactoryBean.getObject() 被调用：
public Object getObject() {
    return feign(context)  // 构建 Feign 代理
        .target(Target.HardCodedTarget.create(UserClient.class, "user-service"));
}

// Feign 底层使用 JDK 动态代理
// InvocationHandler = FeignInvocationHandler

// 调用 userClient.getUser(1L) 时：
FeignInvocationHandler.invoke(proxy, method, args)
      │
      ▼
SynchronousMethodHandler.invoke(args)
      │
      ├──→ 1. 构建 RequestTemplate
      │    解析 @GetMapping("/api/user/{id}")
      │    替换路径变量 → /api/user/1
      │    设置请求头、参数等
      │
      ├──→ 2. 应用 RequestInterceptor 链
      │    如：添加 Authorization 头、traceId 头
      │
      ├──→ 3. 负载均衡（选择目标实例）
      │    LoadBalancerClient.execute("user-service", request)
      │    → 选择 10.244.2.8:8080
      │    → 重写 URL: http://10.244.2.8:8080/api/user/1
      │
      ├──→ 4. 发送 HTTP 请求（通过 Client 实现）
      │    Apache HttpClient / OkHttp / JDK HttpURLConnection
      │
      └──→ 5. 解码响应
           ResponseDecoder.decode(response, UserDTO.class)
           → JSON 反序列化为 UserDTO 对象
```

### 2. Feign 的 Contract 解析

```java
// Contract 负责解析接口上的注解为 Feign 的元数据

// SpringMvcContract 解析 Spring MVC 注解：
@FeignClient(name = "user-service", fallbackFactory = UserClientFallback.class)
interface UserClient {
    
    @GetMapping("/api/user/{id}")           // → GET /api/user/{id}
    UserDTO getUser(@PathVariable Long id); // → 路径参数 id
    
    @PostMapping("/api/user")               // → POST /api/user
    UserDTO createUser(@RequestBody UserDTO user); // → 请求体
    
    @GetMapping("/api/user/search")         // → GET /api/user/search
    List<UserDTO> search(@RequestParam String keyword); // → 查询参数
}

// SpringMvcContract 解析过程：
public class SpringMvcContract extends Contract {
    @Override
    protected void processAnnotationOnMethod(MethodMetadata data, 
                                              Annotation annotation, 
                                              Method method) {
        if (annotation instanceof GetMapping getMapping) {
            // 解析 @GetMapping 的 value 和 produces
            String url = getMapping.value()[0];
            data.template().method(HttpMethod.GET);
            data.template().uri(url);
        }
        if (annotation instanceof PostMapping postMapping) {
            data.template().method(HttpMethod.POST);
        }
    }
    
    @Override
    protected void processAnnotationOnParameter(MethodMetadata data, 
                                                 Annotation[] annotations, 
                                                 int paramIndex) {
        // 解析 @PathVariable → 模板变量
        // 解析 @RequestParam → 查询参数
        // 解析 @RequestBody → 请求体
    }
}
```

### 3. Feign 的重试与熔断集成

```java
// Feign 调用失败时的处理链路

// 重试器（Retryer）
public class Retryer implements Cloneable {
    private final int maxAttempts;     // 最大尝试次数
    private final long period;         // 重试间隔
    private final long maxPeriod;      // 最大重试间隔
    
    public void continueOrPropagate(RetryableException e) {
        if (attempt++ >= maxAttempts) {
            throw e;  // 超过最大重试次数，抛出异常
        }
        // 指数退避
        long interval = Math.min(period * (long) Math.pow(1.5, attempt - 1), maxPeriod);
        Thread.sleep(interval);
    }
}

// 整体调用链：
FeignInvocationHandler.invoke()
      │
      ▼
SynchronousMethodHandler.executeAndDecode()
      │
      ├──→ 调用 Retryer（如果有重试配置）
      │    │
      │    ▼
      ├──→ 调用 Client.execute(request, options)
      │    │
      │    ├──→ 成功 → 返回 Response
      │    │
      │    ├──→ 连接超时/读超时 → RetryableException → Retryer 重试
      │    │
      │    └──→ 服务端 5xx → 判断是否可重试
      │
      ├──→ 调用 ErrorDecoder（解码错误响应）
      │    │
      │    ├──→ 返回 Exception（非重试）
      │    └──→ 返回 RetryableException（触发重试）
      │
      └──→ 熔断器判断（Sentinel/Resilience4j）
           │
           ├──→ 熔断开启 → 直接走 fallback
           └──→ 熔断关闭 → 正常调用
```

---

## 七、配置体系全景图

```
┌─────────────────────────────────────────────────────────────────┐
│                    配置中心 (Nacos Server)                       │
│                                                                  │
│  Namespace: production                                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ shared-configs:                                           │  │
│  │   ├── common-datasource.yaml (DB连接池)                   │  │
│  │   ├── common-redis.yaml (Redis连接)                       │  │
│  │   └── common-logging.yaml (日志格式)                      │  │
│  │                                                           │  │
│  │ extension-configs:                                        │  │
│  │   ├── sentinel-rules.json (限流规则)                      │  │
│  │   └── seata-config.yaml (分布式事务)                      │  │
│  │                                                           │  │
│  │ 应用专属配置:                                              │  │
│  │   ├── order-service.yaml (订单服务独有配置)                │  │
│  │   ├── user-service.yaml                                   │  │
│  │   └── gateway.yaml                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
          Bootstrap 阶段拉取 + 长轮询监听
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Spring Cloud 应用                           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Bootstrap Context                                   │       │
│  │   NacosPropertySourceLocator                        │       │
│  │     → 拉取 shared-configs                           │       │
│  │     → 拉取 extension-configs                        │       │
│  │     → 拉取 app-config                               │       │
│  │     → 注册 Nacos Listener（长轮询）                  │       │
│  └──────────────────┬──────────────────────────────────┘       │
│                     │ 合并 PropertySource                        │
│                     ▼                                           │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Main Application Context                            │       │
│  │                                                     │       │
│  │  Environment.getProperty("spring.datasource.url")   │       │
│  │     → 从合并后的 PropertySource 链逐层查找           │       │
│  │     → 命令行 > Nacos > 本地文件 > 默认值            │       │
│  │                                                     │       │
│  │  @ConfigurationProperties(prefix = "spring")        │       │
│  │     → 从 Environment 绑定属性到 Bean                │       │
│  │     → 配置变更时通过 @RefreshScope 重建 Bean         │       │
│  │                                                     │       │
│  │  @Value("${server.port}")                           │       │
│  │     → 直接从 Environment 注入                       │       │
│  │     → 配置变更时不会自动更新（需要 @RefreshScope）   │       │
│  └─────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 总结

Spring Cloud 配置中间件的底层本质是 **一套围绕 `Environment` 和 `PropertySource` 的扩展体系**：

| 机制 | 底层实现 |
|------|---------|
| **配置加载** | Bootstrap Context → PropertySourceLocator → 从远程拉取注入 Environment |
| **配置优先级** | PropertySources 链式查找，按插入顺序决定优先级 |
| **配置变更通知** | Nacos Long Polling（HTTP 30s hold） + UDP Push（实时性） |
| **Bean 刷新** | @RefreshScope → ScopedProxy → 销毁缓存 → 懒加载重建 |
| **服务注册** | HTTP POST 到 Nacos Server + 定时心跳 PUT |
| **服务发现** | 客户端缓存 + UDP 推送 + 长轮询兜底 |
| **限流规则** | Nacos Listener 监听规则变更 → FlowRuleManager 更新 → 滑动窗口计数 |
| **分布式事务** | DataSourceProxy 拦截 SQL → 记录 undo_log → TC 协调 → 回滚反向执行 |
| **Feign 调用** | JDK 动态代理 → Contract 解析注解 → LoadBalancer 选择实例 → Client 发送请求 |

理解这些底层细节，才能在配置不生效、规则不更新、事务不回滚等问题出现时，快速定位是哪一层出了问题。
