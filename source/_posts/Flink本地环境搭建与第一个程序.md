---
title: Flink 本地环境搭建与第一个程序
date: 2026-08-17 09:15:00
tags:
  - Flink
  - 入门
  - 环境
categories:
  - Flink 新手入门
---

本地跑通第一个 Flink 程序，是入门的第一步。

## 方式一：Standalone 本地集群

```bash
# 下载 Flink 1.19
wget https://archive.apache.org/dist/flink/flink-1.19.0/flink-1.19.0-bin-scala_2.12.tgz
tar xzf flink-1.19.0-bin-scala_2.12.tgz
cd flink-1.19.0

# 启动
./bin/start-cluster.sh

# Web UI: http://localhost:8081
```

## 方式二：Maven 项目（推荐开发）

```xml
<properties>
  <flink.version>1.19.0</flink.version>
  <java.version>11</java.version>
</properties>

<dependencies>
  <dependency>
    <groupId>org.apache.flink</groupId>
    <artifactId>flink-streaming-java</artifactId>
    <version>${flink.version}</version>
  </dependency>
  <dependency>
    <groupId>org.apache.flink</groupId>
    <artifactId>flink-clients</artifactId>
    <version>${flink.version}</version>
  </dependency>
</dependencies>
```

## Hello World：WordCount

```java
import org.apache.flink.api.common.functions.FlatMapFunction;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.util.Collector;

public class WordCount {
    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env =
            StreamExecutionEnvironment.getExecutionEnvironment();

        DataStream<String> text = env.fromElements(
            "hello flink", "hello world", "flink stream"
        );

        DataStream<Tuple2<String, Integer>> counts = text
            .flatMap(new FlatMapFunction<String, Tuple2<String, Integer>>() {
                @Override
                public void flatMap(String line, Collector<Tuple2<String, Integer>> out) {
                    for (String word : line.split(" ")) {
                        out.collect(new Tuple2<>(word, 1));
                    }
                }
            })
            .keyBy(value -> value.f0)
            .sum(1);

        counts.print();
        env.execute("WordCount");
    }
}
```

## 运行

```bash
# IDE 直接运行 main
# 或打包提交
mvn package
./bin/flink run target/wordcount-1.0.jar
```

## 关键概念初识

| 概念 | 说明 |
|------|------|
| `StreamExecutionEnvironment` | 流执行环境 |
| `DataStream` | 数据流 |
| `Transformation` | flatMap、keyBy、sum |
| `Sink` | print()、写入外部系统 |
| `execute()` | 触发作业执行 |

## 常见问题

- **端口 8081 占用**：改 `conf/flink-conf.yaml` 中 `rest.port`
- **Java 版本**：Flink 1.19 需要 Java 11+
- **依赖 scope**：打包集群运行时 connector 不要设为 provided 遗漏

下一篇深入 DataStream 核心概念。
