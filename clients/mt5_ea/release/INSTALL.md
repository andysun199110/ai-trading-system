# Gold AI Trader EA - 安装指南

## 📦 交付内容

本交付包包含以下文件：

```
GoldAITraderEA_RELEASE_v1/
├── GoldAITraderEA_RELEASE_v1.mq5    # EA 源代码文件
├── INSTALL.md                        # 本安装指南
├── PARAMETERS.md                     # 参数配置说明
├── WEBREQUEST_WHITELIST.md           # WebRequest 白名单配置
└── SHADOW_TO_DEMO_CHECKLIST.md       # Shadow→Demo 切换检查清单
```

---

## 🖥️ 系统要求

- **MetaTrader 5** 终端（Build 2245 或更高版本）
- **Windows 10/11** 操作系统
- **稳定的互联网连接**
- **管理员权限**（用于配置 WebRequest 白名单）

---

## 📥 安装步骤

### 步骤 1：定位 MT5 数据目录

1. 打开 MetaTrader 5 终端
2. 点击菜单 **文件 (File)** → **打开数据文件夹 (Open Data Folder)**
3. 在打开的文件夹中，导航到：`MQL5\Experts\`

**完整路径示例：**
```
C:\Users\<你的用户名>\AppData\Roaming\MetaQuotes\Terminal\<终端 ID>\MQL5\Experts\
```

或简写为：
```
%APPDATA%\MetaQuotes\Terminal\<终端 ID>\MQL5\Experts\
```

### 步骤 2：复制 EA 文件

将 `GoldAITraderEA_RELEASE_v1.mq5` 复制到上述 `Experts` 文件夹中。

### 步骤 3：编译 EA

1. 在 MT5 中按 **F4** 打开 MetaEditor
2. 在左侧导航器中找到 **GoldAITraderEA_RELEASE_v1.mq5**
3. 右键点击 → **编译 (Compile)** 或按 **F7**
4. 确认编译成功（输出窗口显示 "0 errors, 0 warnings"）

### 步骤 4：配置 WebRequest 白名单 ⚠️

**这是最关键的一步！没有配置将无法连接 API 服务器。**

1. 在 MT5 中，点击 **工具 (Tools)** → **选项 (Options)** 或按 **Ctrl+O**
2. 切换到 **专家顾问 (Expert Advisors)** 标签页
3. ✅ 勾选 **"允许 WebRequest 访问以下 URL 列表" (Allow WebRequest for listed URL)**
4. 点击 **添加 (Add)**，输入您的 API 服务器地址：
   ```
   https://your-api-domain.com
   ```
   **注意：** 填写 API 源站地址，不是第三方模型地址！
5. 点击 **确定 (OK)** 保存

详细配置说明请参考 `WEBREQUEST_WHITELIST.md`

### 步骤 5：将 EA 添加到图表

1. 在 MT5 导航器中，展开 **专家顾问 (Expert Advisors)**
2. 找到 **GoldAITraderEA_RELEASE_v1**
3. 将其拖拽到 **XAUUSD** 图表上（建议使用 M15 周期）

### 步骤 6：配置参数

在弹出的参数窗口中，配置以下关键参数：

| 参数名 | 建议值 | 说明 |
|--------|--------|------|
| `Inp_ApiBaseUrl` | `https://your-api-domain.com/api/v1` | **必须修改** - 您的 API 服务器地址 |
| `Inp_LicenseKey` | `<您的授权密钥>` | **必须修改** - 从服务提供商获取 |
| `Inp_AccountServer` | `TradeMaxGlobal-Demo` | 您的 MT5 服务器名称 |
| `Inp_ShadowMode` | `true` | 初始建议设为 true（影子模式，不执行交易） |
| `Inp_AllowTrading` | `false` | **保持 false** - 影子/Demo 阶段禁止真实交易 |
| `Inp_PollIntervalSec` | `30` | 信号轮询间隔（秒） |
| `Inp_MaxLotCap` | `0.1` | 最大手数限制 |

完整参数说明请参考 `PARAMETERS.md`

### 步骤 7：启用 AutoTrading

1. 在 MT5 工具栏上，找到 **AutoTrading** 按钮
2. 确保按钮显示为 **绿色播放图标 ▶**（启用状态）
3. 如果是红色方块 ⏹，点击它切换为启用状态

### 步骤 8：验证运行状态

EA 启动后，在图表左上角应显示状态面板：

```
🤖 Gold AI Trader v1.00
Status: ✅ Connected
Mode: 🔒 SHADOW
Account: 60082633
Last Poll: 12:34:56
Position: None
```

**检查日志：**

1. 在 MT5 底部，点击 **工具箱 (Toolbox)** → **专家 (Experts)** 标签
2. 应看到类似日志：
   ```
   [GoldAI] ═══════════════════════════════════════════
   [GoldAI] Gold AI Trader EA v1.00 - RELEASE BUILD
   [GoldAI] ═══════════════════════════════════════════
   [GoldAI] API Endpoint: https://your-api-domain.com/api/v1
   [GoldAI] Operation Mode: 🔒 SHADOW (No Execution)
   [GoldAI] ✅ Initial authentication successful
   [GoldAI] Initialization complete - Ready for operation
   ```

---

## ✅ 安装完成检查清单

- [ ] EA 文件已复制到 `MQL5\Experts\` 目录
- [ ] EA 编译成功（0 errors）
- [ ] WebRequest 白名单已配置
- [ ] EA 已添加到 XAUUSD 图表
- [ ] 参数已正确配置（特别是 API URL 和 License Key）
- [ ] AutoTrading 已启用（绿色▶）
- [ ] 状态面板显示 "✅ Connected"
- [ ] 专家日志显示认证成功

---

## 🔧 故障排查

### 问题 1：状态显示 "❌ Disconnected"

**可能原因：**
- WebRequest 白名单未配置
- API URL 填写错误
- 网络连接问题

**解决方法：**
1. 检查 WebRequest 白名单是否已添加正确的 URL
2. 确认 `Inp_ApiBaseUrl` 参数正确
3. 测试网络连接

### 问题 2：认证失败 "❌ Auth failed"

**可能原因：**
- License Key 未填写或错误
- 账户信息不匹配

**解决方法：**
1. 确认 `Inp_LicenseKey` 已填写正确的授权密钥
2. 确认 `Inp_AccountServer` 与实际 MT5 服务器一致

### 问题 3：无法编译 EA

**可能原因：**
- MT5 版本过旧
- 文件损坏

**解决方法：**
1. 升级 MT5 到最新版本
2. 重新复制 EA 文件

---

## 📋 下一阶段

安装完成后，请参考 `SHADOW_TO_DEMO_CHECKLIST.md` 进行影子模式验证，然后逐步切换到 Demo 模式。

---

## 📞 技术支持

如有问题，请联系服务提供商获取技术支持。
