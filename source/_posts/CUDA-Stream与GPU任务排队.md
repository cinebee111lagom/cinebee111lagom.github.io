---
title: CUDA Stream 与 GPU 任务排队机制
date: 2026-08-12 09:30:00
tags:
  - GPU调度
  - CUDA
categories:
  - GPU调度
---

在 NVIDIA GPU 上，**CUDA Stream** 是最常用的软件层调度单元。可以把 Stream 理解为 GPU 上的「任务队列」：同一 Stream 内任务严格顺序执行，不同 Stream 之间则可以并发。

## Stream 的基本行为

```cuda
cudaStream_t s1, s2;
cudaStreamCreate(&s1);
cudaStreamCreate(&s2);

cudaMemcpyAsync(d_a, h_a, size, cudaMemcpyHostToDevice, s1);
kernel1<<<grid, block, 0, s1>>>(d_a);
cudaMemcpyAsync(h_b, d_b, size, cudaMemcpyDeviceToHost, s2);
```

上述代码中，`s1` 上的拷贝与核函数顺序执行；`s2` 上的回传可与 `s1` 重叠，从而隐藏 PCIe 传输延迟。

## 默认 Stream 的隐式同步

CUDA 规定：**默认 Stream（Stream 0）与所有其他 Stream 之间存在隐式同步**。新手常犯的错误是把所有操作塞进默认 Stream，导致本应并行的传输与计算串行化，GPU 利用率骤降。

生产代码应显式创建非默认 Stream，并配合 `cudaEvent` 做细粒度依赖管理。

## Stream 与硬件调度器

GPU 硬件调度器负责在 SM（Streaming Multiprocessor）上分配 warp。多个 Stream 提交的任务进入同一硬件队列后，调度器会在 warp 阻塞（等内存、等同步）时切换执行其他 warp——这是 **GPU 层面时间复用** 的基础。

但需注意：**Stream 并发不等于无限并行**。显存带宽、L2 缓存、SM 占用率都会成为瓶颈。

## 视频场景中的应用

视频解码后送 GPU 做 resize、色彩空间转换、编码时，典型流水线为：

1. Stream A：DMA 拷贝 YUV 帧到显存
2. Stream B：NVENC/NVDEC 或自定义 kernel 处理
3. Stream C：结果回传或写入显存环形缓冲

三路 Stream 重叠后，单路 4K 转码的吞吐往往可提升 30% 以上。

## 实践建议

- 为 IO、计算、回传分别绑定 Stream
- 避免在热路径频繁 `cudaDeviceSynchronize()`
- 用 Nsight Systems 查看 Stream 时间线，确认是否真正重叠

Stream 是单进程多任务调度的基石；多进程共享 GPU 时，还需要 MPS 或 MIG 等机制，这将在后续文章中展开。
