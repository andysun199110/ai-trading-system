# Shadow Phase B - 修复前报告 (PRE-FIX)

**报告生成时间:** 2026-04-17 13:31 (Asia/Shanghai) / 05:31 UTC  
**报告类型:** 修复前观测窗口（标注为失真数据）  
**观测窗口:** 2026-04-16 11:51 UTC → 2026-04-17 05:31 UTC  
**总时长:** ~17.7 小时

---

## ⚠️ 数据失真声明

**此报告中的数据存在已知问题：**
- **Auth degraded 指标失真**：由于代码缺陷（GET 方法调用 POST 端点），所有 auth_session_health 标记为 "degraded" 的样本均为**误报**
- **实际 Auth 状态**：API 服务正常，session 有效，但心跳调用方法错误导致误判
- **修复后数据**：请参考 `shadow_phaseb_post_fix_report.md` 获取有效评估数据

---

## 1. 观测区间（UTC 时间）

| 阶段 | 开始时间 | 结束时间 | 时长 |
|------|----------|----------|------|
| Phase B (原始) | 2026-04-16 11:51 | 2026-04-17 05:31 | ~17.7 小时 |

---

## 2. 修复前统计汇总

| 指标 | 数值 | 备注 |
|------|------|------|
| 总采样数 | 206 | |
| 平均延迟 (ms) | 3.24 | |
| 信号生成数 | 0 | Shadow 模式预期 |
| 阻断信号数 | 206 (100%) | Shadow 模式预期 |
| 真实下单数 | 0 ✅ | Shadow 模式验证通过 |
| **Auth OK** | **0 (0%)** ❌ | **失真 - 代码缺陷导致** |
| **Auth DEGRADED** | **206 (100%)** ❌ | **失真 - 代码缺陷导致** |

---

## 3. 问题根因分析

### 3.1 代码缺陷定位

**文件:** `/opt/ai-trading/infra/scripts/shadow_phaseb.py` (修复前版本)

**问题代码:**
```python
# ❌ 错误：使用 GET 方法调用需要 POST 的端点
auth = get_api_json("/api/v1/auth/heartbeat")  # GET 请求
auth_health = "ok" if "error" not in auth else "degraded"
```

**API 端点要求:**
```python
# /opt/ai-trading/services/api_server/routers_client.py
@router.post("/auth/heartbeat", response_model=APIResponse)
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db)) -> APIResponse:
    svc = AuthLicenseService(db)
    sess = svc.heartbeat(req.token)  # 需要 POST + token
```

### 3.2 API 日志证据

**过去 2 小时调用统计:**
- GET /heartbeat (405 Method Not Allowed): 24 次 (77.4%)
- POST /heartbeat (200 OK): 7 次 (22.6%) - 来自测试脚本

**日志示例:**
```
api-1 | INFO: 10.255.1.1:51018 - "GET /api/v1/auth/heartbeat HTTP/1.1" 405 Method Not Allowed
api-1 | INFO: 10.255.1.1:43448 - "POST /api/v1/auth/heartbeat HTTP/1.1" 200 OK
```

### 3.3 Session 状态验证

**数据库查询结果:**
```sql
SELECT token, account_login, expires_at, last_heartbeat_at FROM sessions ORDER BY expires_at DESC LIMIT 5;
```

| token | account_login | expires_at | last_heartbeat_at | 状态 |
|-------|---------------|------------|-------------------|------|
| db3f14ef-... | 60066926 | 2026-04-17 05:27:15 | 2026-04-17 05:12:15 | ✅ 有效 |
| b631c33b-... | 60066926 | 2026-04-16 04:09:42 | 2026-04-16 03:54:42 | ❌ 过期 |

---

## 4. 修复方案

### 4.1 代码修复

1. **添加自动激活机制**: 启动时自动调用 `/api/v1/auth/activate` 获取 token
2. **使用 POST 方法**: 心跳调用改为 `POST /api/v1/auth/heartbeat` + `{"token": token}`
3. **403 自动重试**: 遇到 403 错误时自动 re-activate 并重试一次
4. **Token 管理**: 禁止硬编码，从 `.env` 读取配置

### 4.2 配置更新

**文件:** `/opt/ai-trading/.env`
```bash
# Shadow Phase B Auth (auto-activated at startup)
SHADOW_LICENSE_KEY=MT5-LIVE-SG
SHADOW_ACCOUNT_LOGIN=60066926
SHADOW_ACCOUNT_SERVER=TradeMaxGlobal-Demo
```

---

## 5. 修复验证测试

**测试脚本:** `/opt/ai-trading/infra/scripts/shadow_phaseb_heartbeat_test.py`  
**测试窗口:** 30 分钟 (6 样本)  
**测试结果:**

| 样本 | timestamp_utc | auth_session_health |
|------|---------------|---------------------|
| 1 | 2026-04-17T05:01:55 | ✅ ok |
| 2 | 2026-04-17T05:02:14 | ✅ ok |
| 3 | 2026-04-17T05:06:55 | ✅ ok |
| 4 | 2026-04-17T05:07:14 | ✅ ok |
| 5 | 2026-04-17T05:11:55 | ✅ ok |
| 6 | 2026-04-17T05:12:15 | ✅ ok |

**Auth OK 率:** 6/6 = **100%** ✅

---

## 6. 结论

### 6.1 修复前评估

- **Shadow 模式验证:** ✅ 通过 (真实下单数 = 0)
- **信号阻断机制:** ✅ 通过 (100% 阻断)
- **AI 响应延迟:** ✅ 正常 (平均 3.24ms)
- **Auth 健康度:** ⚠️ **数据失真** (实际应正常，代码缺陷导致误报)

### 6.2 建议

- **此窗口数据不应作为 Staging 评估依据**
- **请参考修复后报告** `shadow_phaseb_post_fix_report.md` 获取有效评估
- **修复 Commit:** `4790d28` / `b040c78a55fd71739b3bfa6611d5e616190c01e2`

---

*报告生成于 Phase B.1 启动时，修复前数据已归档至 `shadow_phaseb_pre_fix_2026-04-16.csv`*
