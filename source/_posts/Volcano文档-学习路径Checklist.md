---
title: Volcano 文档：学习路径 Checklist
date: 2026-09-10 17:00:00
tags:
  - Volcano
  - Checklist
categories:
  - Volcano 文档导读
---

## 建议顺序

1. 简介 → 架构 → 安装  
2. VolcanoJob / Queue / PodGroup  
3. Scheduler Overview + gang/proportion  
4. 用户指南：配置调度器、GPU、拓扑  
5. 对接一个生态框架（PyTorch/TF/Spark）  
6. 性能调优与监控  

## 上线检查

- [ ] volcano-system 组件 Ready  
- [ ] 默认 Queue 与租户 Queue 配额清晰  
- [ ] scheduler.conf 入库  
- [ ] Gang 作业 minAvailable 压测通过  
- [ ] GPU/NPU 资源名与插件一致

> 官方文档：[Introduction](https://volcano.sh/zh-Hans/docs/Home/Introduction)

