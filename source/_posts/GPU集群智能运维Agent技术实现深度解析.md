---
title: GPU集群智能运维Agent技术实现深度解析
date: 2026-09-08 09:30:00
tags:
  - GPU
  - 运维
  - Agent
  - Kubernetes
categories:
  - GPU
---

---

## 一、整体架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户层 / 可视化层                              │
│   Grafana Dashboard · Slack/飞书告警 · 成本报告 · 诊断报告           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        Agent 编排层 (Orchestrator)                   │
│                                                                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────────┐  │
│  │ 故障自愈    │ │ 资源优化    │ │ 智能诊断    │ │ 成本分析          │  │
│  │ Agent      │ │ Agent      │ │ Agent      │ │ Agent            │  │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └────────┬─────────┘  │
│        │              │              │                  │            │
│  ┌─────▼──────────────▼──────────────▼──────────────────▼─────────┐  │
│  │                   LLM 推理层 (Reasoning)                       │  │
│  │          任务分解 · 意图理解 · 方案生成 · 结果总结              │  │
│  └─────────────────────────┬──────────────────────────────────────┘  │
│                            │                                         │
│  ┌─────────────────────────▼──────────────────────────────────────┐  │
│  │                   RAG 知识检索层                                │  │
│  │    历史故障库 · 解决方案库 · 集群规范 · K8s 文档               │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        工具执行层 (Tool Execution)                    │
│                                                                      │
│  K8s API · DCGM Exporter · NVIDIA SMI · Prometheus · 日志采集       │
│  Pod 操作 · 节点操作 · 资源配额管理 · 任务调度 API                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心模块详细设计

### 2.1 Agent 框架选型与基础骨架

采用 **ReAct（Reasoning + Acting）** 模式，Agent 可以在"思考"和"行动"之间循环，直到任务完成。

```python
# agent_core.py —— Agent 主循环骨架

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any


class AgentRole(Enum):
    SELF_HEALER = "fault_self_healing"
    RESOURCE_OPTIMIZER = "resource_optimization"
    DIAGNOSTICIAN = "intelligent_diagnosis"
    COST_ANALYST = "cost_analysis"


@dataclass
class ToolCall:
    """LLM 生成的一次工具调用"""
    tool_name: str
    arguments: dict
    thought: str  # LLM 的推理过程


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    output: Any
    error: str | None = None


@dataclass
class AgentStep:
    """Agent 单步记录"""
    thought: str
    tool_call: ToolCall
    result: ToolResult


@dataclass
class AgentSession:
    """一次完整的 Agent 执行会话"""
    session_id: str
    role: AgentRole
    context: dict  # 触发事件的原始数据
    steps: list[AgentStep] = field(default_factory=list)
    final_answer: str = ""
    status: str = "running"


class ToolsRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._descriptions: dict[str, str] = {}

    def register(self, name: str, func: Callable, description: str):
        self._tools[name] = func
        self._descriptions[name] = description

    def execute(self, name: str, arguments: dict) -> ToolResult:
        if name not in self._tools:
            return ToolResult(
                tool_name=name,
                success=False,
                output=None,
                error=f"工具 '{name}' 未注册",
            )
        try:
            result = self._tools[name](**arguments)
            return ToolResult(tool_name=name, success=True, output=result)
        except Exception as e:
            return ToolResult(
                tool_name=name, success=False, output=None, error=str(e)
            )

    def get_tool_descriptions(self) -> str:
        return "\n".join(
            f"- **{name}**: {desc}" for name, desc in self._descriptions.items()
        )


class ReActAgent:
    """ReAct 模式的 Agent 主循环"""

    def __init__(self, llm_client, rag_retriever, tools: ToolsRegistry,
                 max_steps: int = 10):
        self.llm = llm_client
        self.rag = rag_retriever
        self.tools = tools
        self.max_steps = max_steps

    async def run(self, session: AgentSession) -> AgentSession:
        """主循环：Thought -> Action -> Observation -> ... -> Final Answer"""

        system_prompt = self._build_system_prompt(session.role)

        for step_idx in range(self.max_steps):
            # 1. 检索 RAG 相关知识
            rag_context = await self.rag.retrieve(
                query=self._summarize_context(session),
                top_k=5,
            )

            # 2. 构建 prompt
            messages = self._build_messages(
                system_prompt, session, rag_context
            )

            # 3. LLM 推理
            llm_response = await self.llm.chat(messages)

            # 4. 解析 LLM 输出
            parsed = self._parse_llm_output(llm_response)

            if parsed.get("is_final"):
                session.final_answer = parsed["answer"]
                session.status = "completed"
                break

            # 5. 执行工具调用
            tool_call = ToolCall(
                tool_name=parsed["tool_name"],
                arguments=parsed["arguments"],
                thought=parsed["thought"],
            )
            result = self.tools.execute(tool_call.tool_name, tool_call.arguments)

            # 6. 记录步骤
            session.steps.append(
                AgentStep(thought=tool_call.thought, tool_call=tool_call,
                          result=result)
            )

        if session.status != "completed":
            session.status = "max_steps_exceeded"

        return session

    def _build_system_prompt(self, role: AgentRole) -> str:
        role_instructions = {
            AgentRole.SELF_HEALER: """你是一个 GPU 集群故障自愈专家。
当检测到硬件或软件错误时，你需要：
1. 分析错误类型和严重程度
2. 判断是否需要隔离节点
3. 安全地迁移受影响的工作负载
4. 记录故障信息供后续分析""",
            AgentRole.RESOURCE_OPTIMIZER: """你是一个资源优化专家。
你需要：
1. 分析任务历史资源使用数据
2. 对比申请资源与实际使用
3. 计算最优资源配置
4. 生成调整建议并征求用户确认""",
            AgentRole.DIAGNOSTICIAN: """你是一个智能诊断专家。
当任务失败时，你需要：
1. 收集任务日志、事件、环境信息
2. 分类故障原因（代码/资源/环境/权限）
3. 定位根因并给出修复建议
4. 如果有历史类似案例，参考历史解决方案""",
            AgentRole.COST_ANALYST: """你是一个成本分析专家。
你需要：
1. 收集任务资源消耗数据（GPU/CPU/内存/存储）
2. 按团队/项目/用户维度汇总
3. 识别资源浪费和优化机会
4. 生成可视化报告数据""",
        }

        return f"""你是一个 Kubernetes GPU 集群智能运维 Agent。

## 角色定义
{role_instructions[role]}

## 可用工具
{self.tools.get_tool_descriptions()}

## 响应格式
你必须严格按以下 JSON 格式输出，不要输出其他内容：

### 当需要调用工具时：
```json
{{
  "thought": "我的分析思路...",
  "action": {{
    "tool_name": "工具名称",
    "arguments": {{"参数名": "参数值"}}
  }}
}}
```

### 当得出最终结论时：
```json
{{
  "thought": "综合分析...",
  "final_answer": "最终结论和建议"
}}
```

## 约束
- 每次只调用一个工具
- 对于破坏性操作（删除、驱逐），必须先确认风险
- 所有操作必须可追溯、可回滚
- 记录完整的推理链路"""

    def _build_messages(self, system_prompt: str, session: AgentSession,
                        rag_context: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]

        # 注入 RAG 上下文
        if rag_context:
            messages.append({
                "role": "system",
                "content": f"## 历史知识库参考\n{rag_context}",
            })

        # 注入触发事件
        messages.append({
            "role": "user",
            "content": f"## 触发事件\n{json.dumps(session.context, ensure_ascii=False, indent=2)}",
        })

        # 注入历史步骤
        for step in session.steps:
            messages.append({
                "role": "assistant",
                "content": json.dumps({
                    "thought": step.thought,
                    "action": {
                        "tool_name": step.tool_call.tool_name,
                        "arguments": step.tool_call.arguments,
                    }
                }, ensure_ascii=False),
            })
            messages.append({
                "role": "user",
                "content": json.dumps({
                    "tool_name": step.result.tool_name,
                    "success": step.result.success,
                    "output": str(step.result.output)[:2000],
                    "error": step.result.error,
                }, ensure_ascii=False),
            })

        return messages

    def _parse_llm_output(self, output: str) -> dict:
        """解析 LLM 的结构化输出"""
        try:
            data = json.loads(output)
            if "final_answer" in data:
                return {"is_final": True, "answer": data["final_answer"]}
            action = data.get("action", {})
            return {
                "is_final": False,
                "thought": data.get("thought", ""),
                "tool_name": action.get("tool_name", ""),
                "arguments": action.get("arguments", {}),
            }
        except json.JSONDecodeError:
            return {"is_final": True, "answer": output}

    def _summarize_context(self, session: AgentSession) -> str:
        return json.dumps(session.context, ensure_ascii=False)[:1000]
```

---

### 2.2 故障自愈模块（Fault Self-Healing）

#### 2.2.1 事件检测与采集

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ NVIDIA DCGM │───▶│ Prometheus   │───▶│ AlertManager│
│ GPU Xid错误 │    │ 指标采集     │    │ 告警规则    │
│ 温度/功耗   │    │ 聚合存储     │    │ 路由分发    │
└─────────────┘    └──────────────┘    └──────┬──────┘
                                              │
┌─────────────┐    ┌──────────────┐           │
│ dmesg/内核  │───▶│ FluentBit    │───────────┤
│ ECC错误     │    │ 日志解析     │           │
└─────────────┘    └──────────────┘           │
                                              ▼
                                    ┌─────────────────┐
                                    │  Event Router   │
                                    │  (Kafka/Redis)  │
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │  Agent 触发器    │
                                    └─────────────────┘
```

```python
# fault_detection.py —— 故障检测与分类

from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class GPUErrType(Enum):
    """GPU Xid 错误分类"""
    # 致命错误 —— 必须隔离节点
    XID_31 = "GPU_Memory_Page_Retirement"         # 显存页退役
    XID_48 = "Double_Bit_ECC_Error"               # 双比特 ECC 错误
    XID_63 = "ECC_Page_Retirement_Failed"         # 页退役失败
    XID_74 = "NVLink_Error"                       # NVLink 错误
    XID_79 = "GPU_Fell_Off_Bus"                   # GPU 掉线
    XID_94 = "Contained_ECC_Error"                # 可纠正 ECC 错误

    # 软件错误 —— 可尝试恢复
    XID_13 = "Graphics_Launch_Exception"          # 图形启动异常
    XID_32 = "Invalid_or_Illegal_Memory_Access"   # 非法内存访问

    # 未知错误
    UNKNOWN = "Unknown"


# 错误严重程度映射
SEVERITY_MAP = {
    GPUErrType.XID_31: "warning",     # 可继续使用但需关注
    GPUErrType.XID_48: "critical",    # 必须立即隔离
    GPUErrType.XID_63: "critical",    # 必须立即隔离
    GPUErrType.XID_74: "critical",    # NVLink 故障
    GPUErrType.XID_79: "critical",    # GPU 掉线
    GPUErrType.XID_94: "warning",     # 可纠正
    GPUErrType.XID_13: "info",        # 软件层问题
    GPUErrType.XID_32: "warning",     # 可能是应用问题
    GPUErrType.UNKNOWN: "warning",
}


@dataclass
class GPUFaultEvent:
    """GPU 故障事件"""
    event_id: str
    timestamp: datetime
    node_name: str
    gpu_index: int
    gpu_uuid: str
    error_type: GPUErrType
    xid_code: int
    severity: str
    raw_message: str
    affected_pods: list[str]
    affected_jobs: list[str]
    gpu_model: str
    gpu_memory_total_mb: int
    # 历史统计
    xid_count_24h: int       # 该 GPU 过去 24 小时 Xid 次数
    retirement_pages: int     # 已退役显存页数


class DCGMAlertParser:
    """解析 DCGM / Prometheus 告警"""

    def parse_prometheus_alert(self, alert_payload: dict) -> GPUFaultEvent:
        """解析 Prometheus AlertManager 推送的告警"""

        labels = alert_payload.get("labels", {})
        annotations = alert_payload.get("annotations", {})
        xid_code = int(labels.get("xid", 0))

        return GPUFaultEvent(
            event_id=alert_payload.get("fingerprint", ""),
            timestamp=datetime.fromisoformat(
                alert_payload.get("startsAt", "")
            ),
            node_name=labels.get("instance", "").split(":")[0],
            gpu_index=int(labels.get("gpu", "0")),
            gpu_uuid=labels.get("gpu_uuid", ""),
            error_type=self._classify_xid(xid_code),
            xid_code=xid_code,
            severity=SEVERITY_MAP.get(self._classify_xid(xid_code), "unknown"),
            raw_message=annotations.get("description", ""),
            affected_pods=[],  # 后续查询填充
            affected_jobs=[],
            gpu_model=labels.get("modelName", ""),
            gpu_memory_total_mb=int(labels.get("memoryTotal", "0")),
            xid_count_24h=int(labels.get("xid_count_24h", "0")),
            retirement_pages=int(labels.get("retirement_pages", "0")),
        )

    @staticmethod
    def _classify_xid(xid_code: int) -> GPUErrType:
        mapping = {
            31: GPUErrType.XID_31, 48: GPUErrType.XID_48,
            63: GPUErrType.XID_63, 74: GPUErrType.XID_74,
            79: GPUErrType.XID_79, 94: GPUErrType.XID_94,
            13: GPUErrType.XID_13, 32: GPUErrType.XID_32,
        }
        return mapping.get(xid_code, GPUErrType.UNKNOWN)
```

#### 2.2.2 自愈执行引擎

```python
# self_healer.py —— 故障自愈 Agent 工具集

import asyncio
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.rest import ApiException


class SelfHealerTools:
    """故障自愈工具集"""

    def __init__(self):
        config.load_incluster_config()  # 集群内运行
        self.core_v1 = client.CoreV1Api()
        self.batch_v1 = client.BatchV1Api()
        self.custom_api = client.CustomObjectsApi()

    # ──────────────────────────────────────────
    # 工具 1：获取节点上的所有 GPU Pod
    # ──────────────────────────────────────────
    async def get_gpu_pods_on_node(self, node_name: str) -> list[dict]:
        """获取指定节点上所有使用 GPU 的 Pod 及其所属任务"""
        pods = await self.core_v1.list_pod_for_all_namespaces(
            field_selector=f"spec.nodeName={node_name},status.phase=Running"
        )

        gpu_pods = []
        for pod in pods.items:
            # 检查是否请求了 GPU 资源
            has_gpu = False
            gpu_count = 0
            containers = pod.spec.containers or []
            for c in containers:
                limits = (c.resources.limits or {})
                if "nvidia.com/gpu" in limits:
                    has_gpu = True
                    gpu_count += int(limits["nvidia.com/gpu"])

            if has_gpu:
                gpu_pods.append({
                    "namespace": pod.metadata.namespace,
                    "pod_name": pod.metadata.name,
                    "gpu_count": gpu_count,
                    "owner_kind": self._get_owner_kind(pod),
                    "owner_name": self._get_owner_name(pod),
                    "start_time": str(pod.status.start_time),
                    "labels": pod.metadata.labels or {},
                })

        return gpu_pods

    # ──────────────────────────────────────────
    # 工具 2：Cordon 节点（标记不可调度）
    # ──────────────────────────────────────────
    async def cordon_node(self, node_name: str, reason: str) -> dict:
        """将节点标记为不可调度"""
        try:
            body = {
                "spec": {"unschedulable": True},
                "metadata": {
                    "annotations": {
                        "gpu-agent/cordon-reason": reason,
                        "gpu-agent/cordon-time": datetime.utcnow().isoformat(),
                    }
                },
            }
            await self.core_v1.patch_node(node_name, body)
            return {
                "success": True,
                "message": f"节点 {node_name} 已标记为不可调度",
            }
        except ApiException as e:
            return {"success": False, "error": f"cordon 失败: {e.reason}"}

    # ──────────────────────────────────────────
    # 工具 3：驱逐 Pod
    # ──────────────────────────────────────────
    async def evict_pod(self, namespace: str, pod_name: str,
                        grace_period: int = 30) -> dict:
        """安全驱逐一个 Pod"""
        try:
            body = client.V1Eviction(
                metadata=client.V1ObjectMeta(name=pod_name, namespace=namespace),
                delete_options=client.V1DeleteOptions(
                    grace_period_seconds=grace_period,
                ),
            )
            await self.core_v1.create_namespaced_pod_eviction(
                name=pod_name, namespace=namespace, body=body
            )
            return {
                "success": True,
                "message": f"已驱逐 {namespace}/{pod_name}，优雅期 {grace_period}s",
            }
        except ApiException as e:
            return {"success": False, "error": f"驱逐失败: {e.status} {e.reason}"}

    # ──────────────────────────────────────────
    # 工具 4：检查是否有弹性任务可自动重调度
    # ──────────────────────────────────────────
    async def check_elastic_job(self, namespace: str,
                                owner_name: str) -> dict:
        """检查任务是否支持弹性调度（如 PyTorch ElasticJob）"""
        try:
            # 检查是否是 PyTorchJob / ElasticJob
            job = await self.custom_api.get_namespaced_custom_object(
                group="kubeflow.org",
                version="v1",
                namespace=namespace,
                plural="pytorchjobs",
                name=owner_name,
            )
            elastic_config = job.get("spec", {}).get("elasticPolicy")
            return {
                "is_elastic": elastic_config is not None,
                "min_replicas": elastic_config.get("minReplicas", 1) if elastic_config else None,
                "max_replicas": elastic_config.get("maxReplicas", 1) if elastic_config else None,
                "current_replicas": job.get("status", {}).get("replicas", 0),
            }
        except ApiException:
            return {"is_elastic": False, "message": "非弹性任务"}

    # ──────────────────────────────────────────
    # 工具 5：更新节点标签（标记 GPU 健康状态）
    # ──────────────────────────────────────────
    async def label_gpu_health(self, node_name: str, gpu_index: int,
                               health_status: str) -> dict:
        """为节点添加 GPU 健康标签"""
        label_key = f"gpu-agent/gpu-{gpu_index}-health"
        body = {
            "metadata": {
                "labels": {
                    label_key: health_status,  # healthy / degraded / unhealthy
                }
            }
        }
        await self.core_v1.patch_node(node_name, body)
        return {"success": True, "label": f"{label_key}={health_status}"}

    @staticmethod
    def _get_owner_kind(pod) -> str:
        refs = pod.metadata.owner_references or []
        return refs[0].kind if refs else "Pod"

    @staticmethod
    def _get_owner_name(pod) -> str:
        refs = pod.metadata.owner_references or []
        return refs[0].name if refs else pod.metadata.name
```

#### 2.2.3 自愈决策流程图

```
GPU Xid 告警触发
        │
        ▼
   ┌──────────┐    是     ┌─────────────────────┐
   │ 是否致命  │─────────▶│ 立即 cordon 节点     │
   │ Xid 错误？│          └──────────┬────────────┘
   └─────┬────┘                     │
         │ 否                       ▼
         ▼                 ┌─────────────────────┐
   ┌──────────┐    是      │ 获取节点上所有 GPU   │
   │ 24h 内   │──────────▶│ Pod，按优先级排序     │
   │ >= 3 次？│            └──────────┬────────────┘
   └─────┬────┘                      │
         │ 否                        ▼
         ▼                  ┌─────────────────────┐
   ┌──────────┐    是       │ 是否弹性任务？       │
   │ ECC 退役 │───▶ 标记    │   是 → 缩容，自动   │
   │ 页过多？  │   degraded  │   恢复 worker 数    │
   └─────┬────┘            │   否 → evict + 重建  │
         │ 否              └──────────┬────────────┘
         ▼                            │
   记录日志，继续监控                  ▼
                          ┌─────────────────────┐
                          │ 等待 Pod 重新调度    │
                          │ 验证新节点健康       │
                          │ 发送通知             │
                          └─────────────────────┘
```

---

### 2.3 资源优化模块（Resource Optimization）

#### 2.3.1 资源使用分析

```python
# resource_optimizer.py —— 资源使用分析与优化建议

from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np


@dataclass
class ResourceUsageRecord:
    """单次采样的资源使用情况"""
    timestamp: datetime
    pod_name: str
    namespace: str
    # GPU 指标
    gpu_utilization: float       # 0-100%
    gpu_memory_used_mb: float
    gpu_memory_total_mb: float
    gpu_power_watts: float
    # CPU / 内存
    cpu_usage_cores: float
    cpu_request_cores: float
    memory_usage_mb: float
    memory_request_mb: float


@dataclass
class OptimizationRecommendation:
    """优化建议"""
    namespace: str
    workload_name: str
    workload_kind: str           # Deployment / PyTorchJob / etc
    # 当前配置
    current_gpu_request: int
    current_cpu_request: float
    current_memory_request_mb: int
    # 建议配置
    recommended_gpu_request: int
    recommended_cpu_request: float
    recommended_memory_request_mb: int
    # 分析依据
    gpu_util_p50: float
    gpu_util_p95: float
    gpu_util_p99: float
    gpu_memory_peak_mb: float
    cpu_util_p95: float
    memory_util_p95: float
    # 潜在节省
    gpu_saving: int              # 可节省的 GPU 数量
    estimated_monthly_cost_saving: float
    confidence: str              # high / medium / low
    reasoning: str


class ResourceAnalyzer:
    """资源使用分析器"""

    # 优化阈值配置
    GPU_UTIL_THRESHOLD_LOW = 15.0      # GPU 利用率低于此值 → 建议释放
    GPU_MEMORY_THRESHOLD = 0.5         # 显存使用低于总量 50% → 可能用更少卡
    CPU_UTIL_THRESHOLD = 0.3           # CPU 使用率低于申请量 30% → 建议缩减
    MEMORY_UTIL_THRESHOLD = 0.4        # 内存使用低于申请量 40% → 建议缩减
    CONFIDENCE_MIN_SAMPLES = 100       # 至少 100 个采样点才有高置信度

    # 每 GPU 每小时成本（示例值，按实际集群定价）
    COST_PER_GPU_HOUR = 15.0  # 元/小时

    def analyze_workload(
        self,
        records: list[ResourceUsageRecord],
        current_gpu: int,
        current_cpu: float,
        current_memory_mb: int,
    ) -> OptimizationRecommendation | None:
        """分析单个工作负载的资源使用并生成优化建议"""

        if len(records) < 20:
            return None  # 数据量不足

        gpu_utils = np.array([r.gpu_utilization for r in records])
        gpu_mem_used = np.array([r.gpu_memory_used_mb for r in records])
        cpu_utils_pct = np.array([
            r.cpu_usage_cores / max(r.cpu_request_cores, 0.001)
            for r in records
        ])
        mem_utils_pct = np.array([
            r.memory_usage_mb / max(r.memory_request_mb, 1)
            for r in records
        ])

        gpu_util_p50 = float(np.percentile(gpu_utils, 50))
        gpu_util_p95 = float(np.percentile(gpu_utils, 95))
        gpu_util_p99 = float(np.percentile(gpu_utils, 99))
        gpu_mem_peak = float(np.percentile(gpu_mem_used, 99))
        cpu_util_p95 = float(np.percentile(cpu_utils_pct, 95))
        mem_util_p95 = float(np.percentile(mem_utils_pct, 95))

        # ── GPU 优化策略 ──
        recommended_gpu = current_gpu
        reasoning_parts = []

        # 策略 1：所有 GPU 的利用率都很低 → 大量浪费
        if gpu_util_p95 < self.GPU_UTIL_THRESHOLD_LOW:
            # 如果只有少量显存被用，可能只需要 1 卡
            if gpu_mem_peak < records[0].gpu_memory_total_mb * 0.6:
                recommended_gpu = max(1, current_gpu // 2)
                reasoning_parts.append(
                    f"GPU 利用率 P95 仅 {gpu_util_p1:.1f}%，"
                    f"显存峰值 {gpu_mem_peak:.0f}MB "
                    f"(总 {records[0].gpu_memory_total_mb}MB)，"
                    f"建议从 {current_gpu} 卡降至 {recommended_gpu} 卡"
                )

        # 策略 2：申请了多卡但显存只用了一卡的量
        elif (current_gpu > 1 and
              gpu_mem_peak < records[0].gpu_memory_total_mb * 0.8):
            recommended_gpu = max(1, current_gpu - 1)
            reasoning_parts.append(
                f"申请 {current_gpu} 卡但显存峰值 "
                f"{gpu_mem_peak:.0f}MB < 单卡 {records[0].gpu_memory_total_mb}MB，"
                f"建议降至 {recommended_gpu} 卡"
            )

        # ── CPU / 内存优化策略 ──
        recommended_cpu = current_cpu
        recommended_memory = current_memory_mb

        if cpu_util_p95 < self.CPU_UTIL_THRESHOLD:
            recommended_cpu = round(current_cpu * cpu_util_p95 * 1.5, 2)
            recommended_cpu = max(0.5, recommended_cpu)  # 最低 0.5 核
            reasoning_parts.append(
                f"CPU 使用率 P95 仅 {cpu_util_p95*100:.1f}%，"
                f"建议从 {current_cpu} 核降至 {recommended_cpu} 核"
            )

        if mem_util_p95 < self.MEMORY_UTIL_THRESHOLD:
            recommended_memory = int(current_memory_mb * mem_util_p95 * 1.5)
            recommended_memory = max(512, recommended_memory)  # 最低 512MB
            reasoning_parts.append(
                f"内存使用率 P95 仅 {mem_util_p95*100:.1f}%，"
                f"建议从 {current_memory_mb}MB 降至 {recommended_memory}MB"
            )

        # 如果没有优化空间
        if (recommended_gpu == current_gpu and
            recommended_cpu == current_cpu and
            recommended_memory == current_memory_mb):
            return None

        gpu_saving = current_gpu - recommended_gpu
        hours_per_month = 730

        confidence = "high" if len(records) >= self.CONFIDENCE_MIN_SAMPLES else "medium"

        rec = records[0]  # 取第一条的元信息

        return OptimizationRecommendation(
            namespace=rec.namespace,
            workload_name=rec.pod_name.rsplit("-", 1)[0],  # 去掉 pod 哈希后缀
            workload_kind="Unknown",
            current_gpu_request=current_gpu,
            current_cpu_request=current_cpu,
            current_memory_request_mb=current_memory_mb,
            recommended_gpu_request=recommended_gpu,
            recommended_cpu_request=recommended_cpu,
            recommended_memory_request_mb=recommended_memory,
            gpu_util_p50=gpu_util_p50,
            gpu_util_p95=gpu_util_p95,
            gpu_util_p99=gpu_util_p99,
            gpu_memory_peak_mb=gpu_mem_peak,
            cpu_util_p95=cpu_util_p95,
            memory_util_p95=mem_util_p95,
            gpu_saving=gpu_saving,
            estimated_monthly_cost_saving=gpu_saving * self.COST_PER_GPU_HOUR * hours_per_month,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts),
        )
```

---

### 2.4 智能诊断模块（Intelligent Diagnosis）

#### 2.4.1 日志采集与预处理

```python
# diagnosis.py —— 智能诊断 Agent

from dataclasses import dataclass
from enum import Enum


class FailureCategory(Enum):
    CODE_ERROR = "code_error"              # 用户代码错误
    OOM = "out_of_memory"                  # 内存不足
    GPU_OOM = "gpu_out_of_memory"          # GPU 显存不足
    CUDA_ERROR = "cuda_error"              # CUDA 运行时错误
    NCCL_ERROR = "nccl_error"              # 分布式通信错误
    ENVIRONMENT = "environment_error"      # 环境/依赖问题
    PERMISSION = "permission_error"        # 权限问题
    TIMEOUT = "timeout"                    # 超时
    NODE_FAILURE = "node_failure"          # 节点故障
    STORAGE = "storage_error"              # 存储问题（PVC 挂载失败等）
    UNKNOWN = "unknown"


@dataclass
class DiagnosisResult:
    """诊断结果"""
    job_name: str
    namespace: str
    failure_category: FailureCategory
    confidence: float                 # 0.0 - 1.0
    root_cause: str                   # 根因描述
    key_error_lines: list[str]        # 关键错误日志行
    suggested_fixes: list[str]        # 建议修复方案
    similar_cases: list[dict]         # RAG 检索到的类似案例
    full_analysis: str                # LLM 生成的完整分析报告


class LogCollector:
    """日志采集器"""

    def __init__(self):
        config.load_incluster_config()
        self.core_v1 = client.CoreV1Api()

    async def collect_job_logs(
        self, namespace: str, job_name: str, tail_lines: int = 500
    ) -> dict[str, str]:
        """采集任务相关的所有 Pod 日志"""

        # 1. 找到 Job 下所有 Pod
        pods = await self.core_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector="",  # 通过 ownerReferences 查找
        )

        job_pods = []
        for pod in pods.items:
            owners = pod.metadata.owner_references or []
            for owner in owners:
                if owner.name.startswith(job_name):
                    job_pods.append(pod)
                    break

        # 2. 采集每个 Pod 的日志（最近 N 行）
        logs = {}
        for pod in job_pods:
            pod_name = pod.metadata.name
            try:
                log = await self.core_v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    tail_lines=tail_lines,
                    timestamps=True,
                )
                logs[pod_name] = log
            except ApiException as e:
                logs[pod_name] = f"[日志采集失败: {e.reason}]"

            # 还采集 previous 容器的日志（崩溃重启后）
            if pod.status and any(
                cs.restart_count > 0
                for cs in (pod.status.container_statuses or [])
            ):
                try:
                    prev_log = await self.core_v1.read_namespaced_pod_log(
                        name=pod_name,
                        namespace=namespace,
                        tail_lines=tail_lines,
                        timestamps=True,
                        previous=True,
                    )
                    logs[f"{pod_name}[previous]"] = prev_log
                except ApiException:
                    pass

        return logs

    async def collect_pod_events(self, namespace: str,
                                 pod_name: str) -> list[str]:
        """采集 Pod 相关事件"""
        events = await self.core_v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name}",
        )
        return [
            f"[{e.last_timestamp}] {e.reason}: {e.message}"
            for e in events.items
        ]

    async def collect_node_conditions(self, node_name: str) -> dict:
        """采集节点健康状态"""
        node = await self.core_v1.read_node(node_name)
        conditions = {}
        for cond in node.status.conditions or []:
            conditions[cond.type] = {
                "status": cond.status,
                "reason": cond.reason,
                "message": cond.message,
            }
        return conditions


class DiagnosisAgent:
    """智能诊断 Agent"""

    # 规则引擎的快速匹配（LLM 之前先用规则快速分类）
    ERROR_PATTERNS = {
        FailureCategory.GPU_OOM: [
            "CUDA out of memory",
            "OutOfMemoryError",
            "failed to allocate.*CUDA",
            "RuntimeError: CUDA error: out of memory",
        ],
        FailureCategory.OOM: [
            "OOMKilled",
            "Killed",
            "MemoryError",
            "Cannot allocate memory",
        ],
        FailureCategory.CUDA_ERROR: [
            "CUDA error: device-side assert",
            "CUDA error: an illegal memory access",
            "cudaError",
            "CudaError",
            "unspecified launch failure",
        ],
        FailureCategory.NCCL_ERROR: [
            "NCCL ERROR",
            "NCCL.*timeout",
            "ncclCommInitRank",
            "Connection reset by peer.*nccl",
            "Watchdog.*collective.*timeout",
        ],
        FailureCategory.PERMISSION: [
            "PermissionError",
            "Permission denied",
            "AccessDenied",
            "403 Forbidden",
        ],
        FailureCategory.TIMEOUT: [
            "DeadlineExceeded",
            "timed out",
            "TimeoutError",
            "Job has reached the specified backoff limit",
        ],
        FailureCategory.STORAGE: [
            "FailedMount",
            "FailedAttachVolume",
            "PersistentVolumeClaim.*not found",
            "Input/output error",
            "NFS.*stale file handle",
        ],
        FailureCategory.ENVIRONMENT: [
            "ModuleNotFoundError",
            "ImportError",
            "No module named",
            "OSError.*libcudart",
            "libcuda\.so.*cannot open",
            "CUDA driver version is insufficient",
        ],
    }

    def quick_classify(self, log_text: str) -> tuple[FailureCategory, list[str]]:
        """基于规则的快速分类，在调用 LLM 之前使用"""
        import re

        matched_lines = []
        best_category = FailureCategory.UNKNOWN
        best_score = 0

        for category, patterns in self.ERROR_PATTERNS.items():
            score = 0
            for pattern in patterns:
                for line in log_text.split("\n"):
                    if re.search(pattern, line, re.IGNORECASE):
                        score += 1
                        matched_lines.append(line.strip())
            if score > best_score:
                best_score = score
                best_category = category

        return best_category, matched_lines[-10:]  # 最多保留 10 行关键日志

    def build_diagnosis_prompt(
        self,
        namespace: str,
        job_name: str,
        logs: dict[str, str],
        events: list[str],
        node_conditions: dict,
        quick_category: FailureCategory,
        rag_cases: list[dict],
    ) -> str:
        """构建诊断 prompt"""

        # 截取日志（太长放不下）
        log_summaries = []
        for pod_name, log in logs.items():
            # 取最后 200 行
            lines = log.strip().split("\n")[-200:]
            log_summaries.append(f"### Pod: {pod_name}\n```\n" + "\n".join(lines) + "\n```")

        rag_section = ""
        if rag_cases:
            rag_section = "## 历史类似案例\n"
            for i, case in enumerate(rag_cases, 1):
                rag_section += f"""
### 案例 {i}
- **问题**: {case.get('problem', '')}
- **根因**: {case.get('root_cause', '')}
- **解决方案**: {case.get('solution', '')}
- **相似度**: {case.get('score', 0):.2f}
"""

        return f"""## 任务故障诊断请求

### 基本信息
- **命名空间**: {namespace}
- **任务名称**: {job_name}
- **规则引擎初步分类**: {quick_category.value}

### Pod 日志
{"---".join(log_summaries)}

### Pod 事件
```json
{json.dumps(events, ensure_ascii=False, indent=2)}
```

### 节点状态
```json
{json.dumps(node_conditions, ensure_ascii=False, indent=2)}
```

{rag_section}

---

请分析以上信息，输出结构化诊断结果：
```json
{{
  "failure_category": "故障类别",
  "confidence": 0.0-1.0,
  "root_cause": "根因分析",
  "key_error_lines": ["关键错误行1", "关键错误行2"],
  "suggested_fixes": ["修复建议1", "修复建议2"],
  "full_analysis": "详细分析报告"
}}
```"""
```

---

### 2.5 RAG 知识库（Retrieval-Augmented Generation）

#### 2.5.1 知识库构建

```python
# rag_knowledge.py —— RAG 知识库

from dataclasses import dataclass


@dataclass
class KnowledgeDocument:
    """知识文档"""
    doc_id: str
    doc_type: str         # fault_case / solution / doc / runbook
    title: str
    content: str
    metadata: dict
    embedding: list[float] | None = None


class KnowledgeBaseBuilder:
    """知识库构建器"""

    def __init__(self, embedding_model, vector_store):
        self.embedder = embedding_model      # 如 BGE / text2vec
        self.vector_store = vector_store      # 如 Milvus / Qdrant / FAISS

    async def build_from_fault_history(self, fault_records: list[dict]):
        """从历史故障记录构建知识库"""

        documents = []
        for record in fault_records:
            content = f"""
## 故障案例
- **故障类型**: {record['error_type']}
- **Xid Code**: {record.get('xid_code', 'N/A')}
- **节点**: {record['node_name']}
- **GPU**: {record.get('gpu_model', 'N/A')}
- **发生时间**: {record['timestamp']}
- **错误信息**: {record['raw_message']}
- **影响范围**: {record.get('affected_jobs', [])}

## 处理过程
{record.get('resolution_process', '无记录')}

## 根因
{record.get('root_cause', '未确定')}

## 解决方案
{record.get('solution', '无记录')}
"""
            documents.append(KnowledgeDocument(
                doc_id=f"fault_{record['event_id']}",
                doc_type="fault_case",
                title=f"GPU故障: {record['error_type']} - {record['node_name']}",
                content=content,
                metadata={
                    "error_type": record["error_type"],
                    "node_name": record["node_name"],
                    "severity": record.get("severity", ""),
                    "resolved": record.get("resolved", False),
                },
            ))

        # 批量 embedding 并存入向量数据库
        texts = [doc.content for doc in documents]
        embeddings = await self.embedder.encode_batch(texts)
        for doc, emb in zip(documents, embeddings):
            doc.embedding = emb.tolist()

        await self.vector_store.upsert_batch(documents)

    async def build_from_k8s_docs(self, docs_dir: str):
        """从 Kubernetes / NVIDIA 官方文档构建知识库"""
        # 分块策略
        documents = []
        for file_path in Path(docs_dir).glob("**/*.md"):
            content = file_path.read_text(encoding="utf-8")
            chunks = self._split_text(content, max_tokens=512, overlap=64)
            for i, chunk in enumerate(chunks):
                documents.append(KnowledgeDocument(
                    doc_id=f"doc_{file_path.stem}_{i}",
                    doc_type="doc",
                    title=file_path.stem,
                    content=chunk,
                    metadata={"source": str(file_path)},
                ))

        texts = [doc.content for doc in documents]
        embeddings = await self.embedder.encode_batch(texts)
        for doc, emb in zip(documents, embeddings):
            doc.embedding = emb.tolist()

        await self.vector_store.upsert_batch(documents)

    async def add_diagnosis_result(self, diagnosis: 'DiagnosisResult'):
        """将新的诊断结果反哺到知识库"""
        content = f"""
## 诊断记录
- **任务**: {diagnosis.namespace}/{diagnosis.job_name}
- **故障类别**: {diagnosis.failure_category.value}
- **置信度**: {diagnosis.confidence}

## 根因
{diagnosis.root_cause}

## 关键日志
{chr(10).join(diagnosis.key_error_lines)}

## 解决方案
{chr(10).join(diagnosis.suggested_fixes)}

## 完整分析
{diagnosis.full_analysis}
"""
        doc = KnowledgeDocument(
            doc_id=f"diag_{diagnosis.job_name}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            doc_type="solution",
            title=f"诊断记录: {diagnosis.failure_category.value} - {diagnosis.job_name}",
            content=content,
            metadata={
                "category": diagnosis.failure_category.value,
                "confidence": diagnosis.confidence,
                "namespace": diagnosis.namespace,
            },
        )
        embedding = await self.embedder.encode(content)
        doc.embedding = embedding.tolist()
        await self.vector_store.upsert(doc)

    @staticmethod
    def _split_text(text: str, max_tokens: int = 512,
                    overlap: int = 64) -> list[str]:
        """文本分块"""
        sentences = text.split("\n")
        chunks = []
        current_chunk = []
        current_len = 0

        for sentence in sentences:
            token_count = len(sentence.split())
            if current_len + token_count > max_tokens and current_chunk:
                chunks.append("\n".join(current_chunk))
                # 保留 overlap
                overlap_chunk = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    st = len(s.split())
                    if overlap_len + st > overlap:
                        break
                    overlap_chunk.insert(0, s)
                    overlap_len += st
                current_chunk = overlap_chunk
                current_len = overlap_len
            current_chunk.append(sentence)
            current_len += token_count

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks
```

#### 2.5.2 RAG 检索器

```python
# rag_retriever.py —— RAG 检索与重排序

class RAGRetriever:
    """RAG 检索器"""

    def __init__(self, embedding_model, vector_store, reranker=None):
        self.embedder = embedding_model
        self.vector_store = vector_store
        self.reranker = reranker  # 可选的重排序模型（如 bge-reranker）

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        doc_types: list[str] | None = None,
        filters: dict | None = None,
    ) -> str:
        """检索相关知识并格式化为 context"""

        # 1. 向量检索
        query_embedding = await self.embedder.encode(query)
        candidates = await self.vector_store.search(
            embedding=query_embedding.tolist(),
            top_k=top_k * 3,  # 多召回，后续重排
            filters=filters,
        )

        # 2. 按 doc_type 过滤
        if doc_types:
            candidates = [c for c in candidates if c.doc_type in doc_types]

        # 3. 可选：重排序
        if self.reranker and len(candidates) > top_k:
            scores = await self.reranker.rank(
                query=query,
                documents=[c.content for c in candidates],
            )
            candidates = [
                c for _, c in sorted(
                    zip(scores, candidates), key=lambda x: x[0], reverse=True
                )
            ][:top_k]
        else:
            candidates = candidates[:top_k]

        # 4. 格式化输出
        if not candidates:
            return ""

        context_parts = []
        for i, doc in enumerate(candidates, 1):
            context_parts.append(
                f"### 参考 {i} [{doc.doc_type}] (相关度: {doc.score:.2f})\n"
                f"{doc.content}\n"
            )

        return "\n---\n".join(context_parts)
```

---

### 2.6 成本分析模块

```python
# cost_analyzer.py —— 成本追踪与分析

from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TaskCostRecord:
    """任务成本记录"""
    job_name: str
    namespace: str
    user: str
    project: str
    start_time: datetime
    end_time: datetime | None
    duration_hours: float
    # 资源配置
    gpu_model: str
    gpu_count: int
    cpu_cores: float
    memory_gb: float
    # 实际使用
    avg_gpu_utilization: float
    gpu_memory_peak_gb: float
    # 计费
    gpu_hours: float
    wasted_gpu_hours: float    # GPU 利用率 < 10% 的时间
    cost: float
    optimized_cost: float      # 如果按建议配置的估算成本


@dataclass
class CostReport:
    """成本报告"""
    period_start: datetime
    period_end: datetime
    total_cost: float
    total_gpu_hours: float
    total_wasted_gpu_hours: float
    waste_rate: float          # 浪费率
    # 按维度拆分
    by_team: dict[str, float]
    by_project: dict[str, float]
    by_user: dict[str, float]
    by_gpu_model: dict[str, float]
    # Top N 浪费
    top_waste_jobs: list[TaskCostRecord]
    # 优化建议
    potential_savings: float
    recommendations: list[dict]


class CostTracker:
    """成本追踪器"""

    # GPU 单价表（元/小时）
    GPU_PRICING = {
        "NVIDIA-A100-80GB": 18.0,
        "NVIDIA-A100-40GB": 12.0,
        "NVIDIA-V100-32GB": 8.0,
        "NVIDIA-H100-80GB": 28.0,
        "NVIDIA-L40S-48GB": 15.0,
        "NVIDIA-A800-80GB": 16.0,
    }

    GPU_UTIL_WASTE_THRESHOLD = 10.0  # GPU 利用率 < 10% 视为浪费

    def calculate_task_cost(self, record: TaskCostRecord) -> TaskCostRecord:
        """计算单个任务成本"""
        unit_price = self.GPU_PRICING.get(record.gpu_model, 15.0)
        record.gpu_hours = record.gpu_count * record.duration_hours
        record.cost = record.gpu_hours * unit_price

        # 计算浪费的 GPU 小时
        if record.avg_gpu_utilization < self.GPU_UTIL_WASTE_THRESHOLD:
            record.wasted_gpu_hours = record.gpu_hours
        elif record.avg_gpu_utilization < 50:
            # 按比例计算浪费
            unused_ratio = 1 - (record.avg_gpu_utilization / 100)
            record.wasted_gpu_hours = record.gpu_hours * unused_ratio * 0.5
        else:
            record.wasted_gpu_hours = 0

        return record

    def generate_report(
        self,
        records: list[TaskCostRecord],
        period_start: datetime,
        period_end: datetime,
    ) -> CostReport:
        """生成成本报告"""

        total_cost = sum(r.cost for r in records)
        total_gpu_hours = sum(r.gpu_hours for r in records)
        total_wasted = sum(r.wasted_gpu_hours for r in records)

        # 按维度汇总
        by_team = defaultdict(float)
        by_project = defaultdict(float)
        by_user = defaultdict(float)
        by_gpu = defaultdict(float)

        for r in records:
            team = r.namespace.split("-")[0] if "-" in r.namespace else r.namespace
            by_team[team] += r.cost
            by_project[r.project] += r.cost
            by_user[r.user] += r.cost
            by_gpu[r.gpu_model] += r.cost

        # Top 10 浪费任务
        top_waste = sorted(records, key=lambda r: r.wasted_gpu_hours, reverse=True)[:10]

        # 生成优化建议
        recommendations = []
        for r in top_waste[:5]:
            if r.wasted_gpu_hours > 10:
                saving = r.wasted_gpu_hours * self.GPU_PRICING.get(r.gpu_model, 15) * 0.5
                recommendations.append({
                    "job": f"{r.namespace}/{r.job_name}",
                    "user": r.user,
                    "issue": f"GPU 利用率仅 {r.avg_gpu_utilization:.1f}%，"
                             f"浪费 {r.wasted_gpu_hours:.1f} GPU 小时",
                    "suggestion": f"建议将 GPU 从 {r.gpu_count} 卡降至 "
                                  f"{max(1, r.gpu_count // 2)} 卡",
                    "potential_saving": f"¥{saving:.0f}/月",
                })

        return CostReport(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            total_gpu_hours=total_gpu_hours,
            total_wasted_gpu_hours=total_wasted,
            waste_rate=total_wasted / max(total_gpu_hours, 1),
            by_team=dict(by_team),
            by_project=dict(by_project),
            by_user=dict(by_user),
            by_gpu_model=dict(by_gpu),
            top_waste_jobs=top_waste,
            potential_savings=sum(
                r.wasted_gpu_hours * self.GPU_PRICING.get(r.gpu_model, 15) * 0.5
                for r in records if r.wasted_gpu_hours > 10
            ),
            recommendations=recommendations,
        )
```

---

## 三、底层基础设施细节

### 3.1 GPU 指标采集链路

```
┌─────────────┐   dcgm-exporter    ┌──────────────┐   告警规则   ┌──────────┐
│  NVIDIA GPU  │───────────────────▶│  Prometheus   │────────────▶│ Alert    │
│  DCGM 守护   │  :9400/metrics     │  TSDB 存储    │  聚合计算   │ Manager  │
│  进程        │                    │              │            │          │
└─────────────┘                    └──────┬───────┘            └────┬─────┘
                                          │                        │
                                    Grafana Dashboard          Agent Webhook
```

```yaml
# DCGM Exporter 关键指标
# 每 15 秒采集一次

# GPU 利用率
DCGM_FI_DEV_GPU_UTIL                    # GPU 计算利用率 (%)
DCGM_FI_DEV_MEM_COPY_UTIL               # 显存拷贝利用率 (%)

# 显存
DCGM_FI_DEV_FB_FREE                     # 空闲显存 (MiB)
DCGM_FI_DEV_FB_USED                     # 已用显存 (MiB)

# 温度与功耗
DCGM_FI_DEV_GPU_TEMP                    # GPU 温度 (°C)
DCGM_FI_DEV_POWER_USAGE                 # 当前功耗 (W)

# 错误计数
DCGM_FI_DEV_XID_ERRORS                  # Xid 错误计数 (累计)
DCGM_FI_DEV_ECC_SBE_VOL                 # 单比特 ECC 错误 (volatile)
DCGM_FI_DEV_ECC_DBE_VOL                 # 双比特 ECC 错误 (volatile)

# PCIe / NVLink
DCGM_FI_DEV_PCIE_TX_THROUGHPUT          # PCIe 发送吞吐
DCGM_FI_DEV_PCIE_RX_THROUGHPUT          # PCIe 接收吞吐
DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL      # NVLink 总带宽
```

```yaml
# Prometheus 告警规则示例
groups:
  - name: gpu-fault-detection
    rules:
      # Xid 错误检测
      - alert: GPUXidError
        expr: increase(DCGM_FI_DEV_XID_ERRORS[5m]) > 0
        for: 0s
        labels:
          severity: critical
        annotations:
          summary: "GPU Xid 错误: {{ $labels.gpu }} on {{ $labels.instance }}"
          description: "Xid 错误计数在过去5分钟增加 {{ $value }}"

      # 双比特 ECC 错误（致命）
      - alert: GPUDoubleBitECC
        expr: increase(DCGM_FI_DEV_ECC_DBE_VOL[1m]) > 0
        for: 0s
        labels:
          severity: critical
        annotations:
          summary: "GPU 双比特 ECC 错误: {{ $labels.gpu }}"
          description: "需要立即隔离该 GPU"

      # GPU 温度过高
      - alert: GPUOverheat
        expr: DCGM_FI_DEV_GPU_TEMP > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU 温度过高: {{ $value }}°C"

      # GPU 利用率持续为 0（闲置浪费检测）
      - alert: GPUIdleWaste
        expr: DCGM_FI_DEV_GPU_UTIL < 5 and on() DCGM_FI_DEV_FB_USED > 1024
        for: 2h
        labels:
          severity: info
        annotations:
          summary: "GPU 已闲置 2 小时但占用显存"
```

### 3.2 节点操作安全机制

```python
# safety.py —— 操作安全网

import hashlib
from datetime import datetime, timedelta


class OperationSafetyGuard:
    """操作安全防护网"""

    def __init__(self, redis_client, notification_service):
        self.redis = redis_client
        self.notifier = notification_service

    # ── 规则 1：cordon 频率限制 ──
    async def check_cordon_rate_limit(self, node_name: str,
                                      max_per_hour: int = 3) -> bool:
        """防止频繁 cordon 节点"""
        key = f"cordon_count:{node_name}:{datetime.utcnow().strftime('%Y%m%d%H')}"
        count = await self.redis.incr(key)
        await self.redis.expire(key, 3600)
        if count > max_per_hour:
            return False  # 拒绝操作
        return True

    # ── 规则 2：集群最小可用节点数 ──
    async def check_min_ready_nodes(self, core_v1_api,
                                    min_ready: int = 3) -> bool:
        """确保集群中始终有足够可用节点"""
        nodes = await core_v1_api.list_node()
        ready_count = sum(
            1 for node in nodes.items
            if node.spec.unschedulable is not True
            and any(
                c.type == "Ready" and c.status == "True"
                for c in (node.status.conditions or [])
            )
        )
        return ready_count > min_ready

    # ── 规则 3：关键任务保护 ──
    async def check_critical_workload(self, namespace: str,
                                      pod_name: str) -> bool:
        """检查是否是关键任务，关键任务需要人工确认"""
        key = f"critical_check:{namespace}:{pod_name}"
        cached = await self.redis.get(key)
        if cached:
            return cached == "approved"

        # 检查标签
        config.load_incluster_config()
        core_v1 = client.CoreV1Api()
        pod = await core_v1.read_namespaced_pod(pod_name, namespace)
        labels = pod.metadata.labels or {}

        if labels.get("priority") == "critical" or \
           labels.get("gpu-agent/auto-evict") == "disabled":
            # 通知人工审批
            await self.notifier.send_approval_request(
                title=f"关键任务驱逐审批: {namespace}/{pod_name}",
                message="该任务标记为关键任务，自动驱逐需要人工确认。",
                callback_key=key,
            )
            return False  # 暂不执行，等待审批

        return True  # 非关键任务，可以执行

    # ── 规则 4：操作审计日志 ──
    async def log_operation(self, operation: dict):
        """所有 Agent 操作都记入审计日志"""
        audit_entry = {
            **operation,
            "timestamp": datetime.utcnow().isoformat(),
            "operation_hash": hashlib.sha256(
                json.dumps(operation, sort_keys=True).encode()
            ).hexdigest()[:16],
        }
        await self.redis.lpush("agent:audit_log", json.dumps(audit_entry))
        await self.redis.ltrim("agent:audit_log", 0, 9999)  # 保留最近 1 万条
```

### 3.3 LLM 接入层

```python
# llm_client.py —— LLM 调用封装

import httpx
from typing import AsyncIterator


class LLMClient:
    """LLM 统一调用客户端"""

    def __init__(self, config: dict):
        self.provider = config.get("provider", "openai_compatible")
        self.base_url = config["base_url"]        # 如 vLLM / Ollama / 私有部署
        self.api_key = config.get("api_key", "")
        self.model = config["model"]              # 如 qwen2.5-72b / deepseek-v3
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.1)  # Agent 任务用低温
        self.timeout = config.get("timeout", 120)
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def chat(self, messages: list[dict],
                   tools: list[dict] | None = None) -> str:
        """调用 LLM Chat Completion"""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},  # 强制 JSON 输出
        }
        if tools:
            payload["tools"] = tools

        response = await self.client.post(
            f"{self.base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


# ── Embedding 模型 ──

class EmbeddingClient:
    """Embedding 模型调用"""

    def __init__(self, base_url: str, model: str = "bge-large-zh-v1.5"):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=30)

    async def encode(self, text: str) -> list[float]:
        response = await self.client.post(
            f"{self.base_url}/v1/embeddings",
            json={"model": self.model, "input": text},
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    async def encode_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.post(
            f"{self.base_url}/v1/embeddings",
            json={"model": self.model, "input": texts},
        )
        response.raise_for_status()
        return [item["embedding"] for item in response.json()["data"]]
```

---

## 四、部署架构

### 4.1 Kubernetes 部署拓扑

```
┌─── gpu-agent-system namespace ────────────────────────────────────────┐
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ agent-controller │  │ event-router     │  │ llm-proxy (可选)     │ │
│  │ (Deployment)     │  │ (Deployment)     │  │ (Deployment)         │ │
│  │ - 故障自愈循环   │  │ - Kafka 消费     │  │ - vLLM / Ollama      │ │
│  │ - 资源优化定时   │  │ - 事件分类路由   │  │ - 本地推理           │ │
│  │ - 诊断服务       │  │                  │  │                      │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘ │
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ vector-store     │  │ redis            │  │ prometheus           │ │
│  │ (StatefulSet)    │  │ (StatefulSet)    │  │ (Operator)           │ │
│  │ - Qdrant/FAISS   │  │ - 状态缓存       │  │ - 指标存储           │ │
│  │ - RAG 知识库     │  │ - 审计日志       │  │ - 告警规则           │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘ │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ RBAC: ServiceAccount gpu-agent-sa                               │ │
│  │ - nodes: get, list, patch (cordon/label)                        │ │
│  │ - pods: get, list, delete, create-eviction                      │ │
│  │ - events: get, list                                             │ │
│  │ - jobs/pytorchjobs: get, list, patch                            │ │
│  │ - persistentvolumeclaims: get, list                             │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.2 RBAC 配置

```yaml
# rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gpu-agent-role
rules:
  # 节点操作（cordon/uncordon/label）
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["get", "list", "watch", "patch"]
  # Pod 操作（驱逐/查询日志）
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch", "delete", "create"]
  - apiGroups: [""]
    resources: ["pods/eviction"]
    verbs: ["create"]
  # Pod 日志
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
  # 事件
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["get", "list", "watch"]
  # PyTorchJob / ElasticJob
  - apiGroups: ["kubeflow.org"]
    resources: ["pytorchjobs", "tfjobs", "mpijobs"]
    verbs: ["get", "list", "watch", "patch"]
  # Spark Application（如果有）
  - apiGroups: ["sparkoperator.k8s.io"]
    resources: ["sparkapplications"]
    verbs: ["get", "list", "watch"]
  # PVC
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list"]
```

---

## 五、数据流全景

```
                     ┌──────────────────────────────────────┐
                     │              数据源层                 │
                     │                                      │
                     │  DCGM ←→ GPU 硬件                    │
                     │  dmesg ←→ 内核日志                    │
                     │  kubelet ←→ K8s 事件                 │
                     │  task-scheduler ←→ 任务状态           │
                     └──────────────┬───────────────────────┘
                                    │ 采集
                     ┌──────────────▼───────────────────────┐
                     │              存储层                   │
                     │                                      │
                     │  Prometheus (时序指标)                │
                     │  Elasticsearch/Loki (日志)            │
                     │  Qdrant/Milvus (向量知识库)           │
                     │  Redis (状态缓存/审计)                │
                     │  PostgreSQL (结构化记录)              │
                     └──────────────┬───────────────────────┘
                                    │ 查询
                     ┌──────────────▼───────────────────────┐
                     │              推理层                   │
                     │                                      │
                     │  规则引擎 (快速分类/阈值告警)         │
                     │      ↓ 不确定时                      │
                     │  LLM + RAG (深度分析/方案生成)       │
                     └──────────────┬───────────────────────┘
                                    │ 决策
                     ┌──────────────▼───────────────────────┐
                     │              执行层                   │
                     │                                      │
                     │  K8s API (cordon/evict/scale/patch)   │
                     │  任务调度 API (重提交/调整资源)       │
                     │  通知系统 (Slack/飞书/邮件)           │
                     └──────────────┬───────────────────────┘
                                    │ 反馈
                     ┌──────────────▼───────────────────────┐
                     │              反馈层                   │
                     │                                      │
                     │  操作结果 → 审计日志                  │
                     │  诊断结果 → 知识库反哺                │
                     │  优化效果 → 指标追踪                  │
                     └──────────────────────────────────────┘
```

---

## 六、关键设计决策总结

| 维度 | 决策 | 原因 |
|------|------|------|
| **Agent 框架** | ReAct 模式，自研轻量实现 | 可控性强，避免 LangChain 等重依赖；GPU 集群场景工具集明确，不需要复杂编排 |
| **LLM 选型** | 私有部署 Qwen2.5-72B / DeepSeek-V3 | 日志含敏感信息不可外传；72B 级别足够理解复杂日志和生成方案 |
| **规则 vs LLM** | 双层架构：规则引擎快速分流 + LLM 深度分析 | 90% 的常见故障（OOM、Xid 已知编号）规则可秒级处理；LLM 只处理复杂/未知场景，降低延迟和成本 |
| **RAG 向量库** | Qdrant / Milvus，BGE-Large-Zh 嵌入 | 中文日志和文档需要中文 embedding；BGE 在中文场景效果好 |
| **操作安全** | RBAC 最小权限 + 频率限制 + 关键任务保护 + 审计 | Agent 有节点和 Pod 操作权限，必须有多层防护避免误操作 |
| **指标采集** | DCGM Exporter + Prometheus | 业界标准，生态成熟，原生支持 GPU 详细指标 |
| **成本计算** | GPU-hours 模型，按 GPU 型号定价 | GPU 是集群最贵资源，以此为计费单位直观 |

这套系统的核心思路是：**用规则引擎处理确定性问题（快），用 LLM 处理模糊性问题（准），用 RAG 持续积累经验（越用越好），用多层安全机制确保操作可控（稳）。**
