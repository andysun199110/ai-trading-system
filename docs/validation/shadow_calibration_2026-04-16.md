# Shadow Phase A.1 Calibration Report

**Report Generated:** 2026-04-16T11:49 UTC  
**Calibration Window:** 11:18 - 11:48 UTC (30 minutes)  
**Status:** ✅ PASSED

---

## 1. 校准要求验证

| 要求 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 采样间隔 | 5 分钟 | 300.11 秒 (5.00 分钟) | ✅ |
| 记录数 | ≥6 条 | 6 条数据 + 1 header | ✅ |
| 时间容差 | ±30 秒 | 所有间隔在范围内 | ✅ |
| 采样中断 | 无 | 无中断 | ✅ |

---

## 2. 采样数据

| # | Timestamp (UTC) | AI Latency (ms) | Auth Health | Signals | Blocked | Duplicate Check |
|---|-----------------|-----------------|-------------|---------|---------|-----------------|
| 1 | 11:18:51 | 6.22 | degraded | 0 | 1 | passed |
| 2 | 11:23:52 | 3.02 | degraded | 0 | 1 | passed |
| 3 | 11:28:52 | 3.13 | degraded | 0 | 1 | passed |
| 4 | 11:33:52 | 2.87 | degraded | 0 | 1 | passed |
| 5 | 11:38:52 | 2.98 | degraded | 0 | 1 | passed |
| 6 | 11:43:52 | 2.93 | degraded | 0 | 1 | passed |
| 7 | 11:48:52 | 2.76 | degraded | 0 | 1 | passed |

---

## 3. 统计汇总

| 指标 | 均值 | P95 | 最大值 | 最小值 |
|------|------|-----|--------|--------|
| AI Response Latency (ms) | 3.42 | 6.22 | 6.22 | 2.76 |
| Auth Session Health | degraded | - | - | - |
| Signal Count | 0 | 0 | 0 | 0 |
| Blocked Reasons | 1 | 1 | 1 | 1 |

---

## 4. 间隔分析

| 间隔 | 时长 (秒) | 状态 |
|------|-----------|------|
| 1→2 | 300.16 | ✅ |
| 2→3 | 300.11 | ✅ |
| 3→4 | 300.11 | ✅ |
| 4→5 | 300.10 | ✅ |
| 5→6 | 300.10 | ✅ |
| 6→7 | 300.10 | ✅ |

**平均间隔:** 300.11 秒 (5.00 分钟)  
**容差范围:** 270-330 秒  
**所有间隔:** 在容差范围内 ✅

---

## 5. 交付物

| 文件 | 路径 | 状态 |
|------|------|------|
| 校准报告 | `docs/validation/shadow_calibration_2026-04-16.md` | ✅ |
| 校准数据 | `artifacts/shadow_calibration_2026-04-16.csv` | ✅ (7 行) |

---

## 6. 结论

**✅ Phase A.1 校准通过**

- 采样器工作正常
- 间隔精确（5 分钟 ±0.11 秒）
- 所有必填字段完整
- 无采样中断

**建议：启动 Phase B (24h 延长观测)**

---

*Calibration completed by Shadow Metrics Collector v2.0*
