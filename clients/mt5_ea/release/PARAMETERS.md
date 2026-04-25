# Gold AI Trader EA - 参数配置说明

## 📝 参数分组

EA 参数分为三大组，在 MT5 参数窗口中按组显示。

---

## 🔑 第一组：API Configuration（API 配置）

**这组参数必须正确配置，否则 EA 无法连接服务器。**

### `Inp_ApiBaseUrl`
- **类型：** string（字符串）
- **默认值：** `https://your-api-domain.com/api/v1`
- **说明：** API 服务器的基础 URL
- **⚠️ 必须修改：** 是
- **示例：** `https://api.yourcompany.com/api/v1`

**注意：** 填写您的 API 源站地址，不是第三方 AI 模型地址！

---

### `Inp_LicenseKey`
- **类型：** string（字符串）
- **默认值：** `""`（空）
- **说明：** 授权许可证密钥
- **⚠️ 必须修改：** 是
- **获取方式：** 从服务提供商获取

**⚠️ 重要：** 不填写此参数将无法通过身份认证！

---

### `Inp_PollIntervalSec`
- **类型：** int（整数）
- **默认值：** `30`
- **说明：** 信号轮询间隔（秒）
- **建议值：** `30`（30 秒）
- **范围：** 10 - 300

**说明：** EA 每隔多久向服务器查询一次新信号。过短会增加服务器负载，过长可能错过交易机会。

---

## 👤 第二组：Account Settings（账户设置）

### `Inp_AccountServer`
- **类型：** string（字符串）
- **默认值：** `""`（空）
- **说明：** MT5 账户所在的服务器名称
- **⚠️ 必须修改：** 是
- **示例：** `TradeMaxGlobal-Demo`、`ICMarkets-Demo`

**如何查找：**
1. 在 MT5 中，右键点击账户名
2. 选择"属性"
3. 查看"服务器"字段

---

### `Inp_ShadowMode`
- **类型：** bool（布尔）
- **默认值：** `true`
- **说明：** 影子模式开关
- **推荐设置：**
  - 初始验证阶段：`true`
  - Demo 实盘测试：`true`
  - 真实交易：`false`

**影子模式说明：**
- `true`：EA 接收信号但**不执行实际交易**，仅记录日志
- `false`：EA 根据信号执行实际交易

**⚠️ 强烈建议：** 首次部署时保持 `true`，验证系统运行正常后再考虑切换。

---

### `Inp_DefaultLotSize`
- **类型：** double（浮点数）
- **默认值：** `0.01`
- **说明：** 默认交易手数
- **建议值：** `0.01` - `0.1`（根据账户资金和风险承受能力）

**说明：** 当服务器未返回具体手数建议时使用此值。

---

## 🛡️ 第三组：Risk Management（风险管理）

### `Inp_StopLossPoints`
- **类型：** int（整数）
- **默认值：** `500`
- **说明：** 止损点数
- **XAUUSD 示例：** 500 点 = 5 美元（黄金每点 0.01 美元）

---

### `Inp_TakeProfitPoints`
- **类型：** int（整数）
- **默认值：** `1000`
- **说明：** 止盈点数
- **XAUUSD 示例：** 1000 点 = 10 美元

---

### `Inp_AllowTrading` ⚠️
- **类型：** bool（布尔）
- **默认值：** `false`
- **说明：** 是否允许真实交易执行
- **推荐设置：**
  - Shadow 阶段：`false`
  - Demo 阶段：`false`
  - 真实交易：`true`（仅在完全验证后）

**⚠️ 安全警告：**
- 此参数为**最终交易开关**
- 即使 `Inp_ShadowMode=false`，如果此参数为 `false`，交易也不会执行
- 双重保护设计，防止意外交易

---

### `Inp_RequireServerRiskParams`
- **类型：** bool（布尔）
- **默认值：** `true`
- **说明：** 是否要求使用服务器端风险参数

**说明：**
- `true`：优先使用服务器返回的风险参数（止损、止盈、手数等）
- `false`：仅使用本地配置的参数

**推荐：** 保持 `true`，让服务器统一管理风险。

---

### `Inp_UseFallbackRiskParams`
- **类型：** bool（布尔）
- **默认值：** `false`
- **说明：** 服务器不可用时是否使用本地 fallback 参数

**说明：**
- `true`：服务器连接失败时，使用本地配置的参数继续交易
- `false`：服务器连接失败时，暂停交易

**推荐：** 保持 `false`，服务器离线时暂停交易更安全。

---

### `Inp_MaxLotCap`
- **类型：** double（浮点数）
- **默认值：** `0.1`
- **说明：** 最大手数上限
- **建议值：** `0.1` - `0.2`（根据账户规模）

**说明：** 无论服务器建议多少手数，实际执行不会超过此上限。这是重要的风险控制措施。

---

## 📋 推荐配置模板

### Shadow 阶段配置（初始验证）

```
Inp_ApiBaseUrl              = https://your-api-domain.com/api/v1
Inp_LicenseKey              = <your-license-key>
Inp_PollIntervalSec         = 30
Inp_AccountServer           = TradeMaxGlobal-Demo
Inp_ShadowMode              = true
Inp_DefaultLotSize          = 0.01
Inp_StopLossPoints          = 500
Inp_TakeProfitPoints        = 1000
Inp_AllowTrading            = false  ⚠️ 必须为 false
Inp_RequireServerRiskParams = true
Inp_UseFallbackRiskParams   = false
Inp_MaxLotCap               = 0.1
```

### Demo 阶段配置（模拟盘测试）

```
Inp_ApiBaseUrl              = https://your-api-domain.com/api/v1
Inp_LicenseKey              = <your-license-key>
Inp_PollIntervalSec         = 30
Inp_AccountServer           = TradeMaxGlobal-Demo
Inp_ShadowMode              = true  ⚠️ 仍建议保持 true
Inp_DefaultLotSize          = 0.01
Inp_StopLossPoints          = 500
Inp_TakeProfitPoints        = 1000
Inp_AllowTrading            = false  ⚠️ Demo 阶段也建议为 false
Inp_RequireServerRiskParams = true
Inp_UseFallbackRiskParams   = false
Inp_MaxLotCap               = 0.1
```

**说明：** Demo 阶段仍建议保持 Shadow 模式，因为：
1. 可以验证信号接收和解析逻辑
2. 可以观察策略表现
3. 无风险，可随时调整参数

### Live 阶段配置（真实交易）⚠️

```
Inp_ApiBaseUrl              = https://your-api-domain.com/api/v1
Inp_LicenseKey              = <your-license-key>
Inp_PollIntervalSec         = 30
Inp_AccountServer           = <your-live-server>
Inp_ShadowMode              = false  ⚠️ 仅在此阶段设为 false
Inp_DefaultLotSize          = 0.01
Inp_StopLossPoints          = 500
Inp_TakeProfitPoints        = 1000
Inp_AllowTrading            = true   ⚠️ 仅在完全验证后设为 true
Inp_RequireServerRiskParams = true
Inp_UseFallbackRiskParams   = false
Inp_MaxLotCap               = 0.1    ⚠️ 根据账户规模调整
```

**⚠️ 重要警告：**
- 仅在 Shadow 和 Demo 阶段充分验证后才考虑切换到 Live 模式
- 切换前务必完成 `SHADOW_TO_DEMO_CHECKLIST.md` 中的所有检查项
- 建议先用最小手数（0.01）测试

---

## 🔧 如何修改参数

### 方法 1：添加 EA 时配置
1. 将 EA 拖拽到图表时，会弹出参数窗口
2. 修改参数后点击"确定"

### 方法 2：运行时修改
1. 右键点击图表上的 EA 图标
2. 选择"属性 (Properties)"或按 **Ctrl+E**
3. 在"输入 (Inputs)"标签页修改参数
4. 点击"确定"
5. ⚠️ 某些参数修改后 EA 会重新初始化

### 方法 3：保存预设
1. 配置好参数后，点击"预设 (Presets)" → "保存 (Save)"
2. 输入预设名称（如 "Shadow_Safe"）
3. 下次可直接加载预设

---

## 📊 参数验证清单

在开始运行前，请确认：

- [ ] `Inp_ApiBaseUrl` 已修改为正确的 API 地址
- [ ] `Inp_LicenseKey` 已填写有效的授权密钥
- [ ] `Inp_AccountServer` 与实际 MT5 服务器一致
- [ ] `Inp_ShadowMode` 初始设为 `true`
- [ ] `Inp_AllowTrading` 初始设为 `false`
- [ ] `Inp_MaxLotCap` 设置为可接受的风险水平
- [ ] WebRequest 白名单已配置（见 `WEBREQUEST_WHITELIST.md`）

---

## 📞 需要帮助？

如不确定参数如何配置，请联系服务提供商获取技术支持。
