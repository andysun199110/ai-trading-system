# WebRequest 白名单配置指南

## ⚠️ 为什么需要配置 WebRequest 白名单？

MetaTrader 5 出于安全考虑，**默认禁止 EA 访问外部网络**。EA 必须经过显式授权才能通过 WebRequest 函数连接 API 服务器。

**未配置白名单的后果：**
- EA 无法连接 API 服务器
- 认证失败（HTTP 0 错误）
- 无法接收交易信号
- 状态面板显示 "❌ Disconnected"

---

## 📋 配置步骤

### 步骤 1：打开 MT5 选项

1. 在 MT5 主界面，点击菜单 **工具 (Tools)**
2. 选择 **选项 (Options)**
3. 或使用快捷键 **Ctrl + O**

### 步骤 2：切换到专家顾问标签

在选项窗口中，点击 **专家顾问 (Expert Advisors)** 标签页

### 步骤 3：启用 WebRequest 权限

1. ✅ 勾选 **"允许 WebRequest 访问以下 URL 列表" (Allow WebRequest for listed URL)**

   **截图说明：**
   ```
   ☑ Allow WebRequest for listed URL
   ```

### 步骤 4：添加 API 服务器地址

1. 点击 **添加 (Add)** 按钮
2. 输入您的 API 服务器地址

**⚠️ 重要：填写规则**

| ❌ 错误示例 | ✅ 正确示例 |
|------------|------------|
| `https://api.deepseek.com` | `https://your-api-domain.com` |
| `https://openai.com` | `https://api.yourcompany.com` |
| 第三方模型地址 | **您的 API 源站地址** |

**说明：**
- WebRequest 白名单应填写**您的 API 源站地址**，不是第三方 AI 模型提供商的地址
- EA 连接的是您的 API 服务器，由您的服务器再去调用第三方模型
- 示例：`https://api.goldaitrader.com` 或 `https://trading.yourcompany.com`

3. 点击 **确定 (OK)** 保存

### 步骤 5：确认配置

添加后，URL 列表应显示您的 API 服务器地址：

```
Allowed URLs:
├─ https://your-api-domain.com
└─ (可添加多个)
```

### 步骤 6：保存并重启

1. 点击 **确定 (OK)** 关闭选项窗口
2. **重启 MT5 终端**（确保配置生效）
3. 重新将 EA 添加到图表

---

## 🔍 验证配置是否生效

### 方法 1：检查 EA 状态

1. 将 EA 添加到图表后，观察状态面板
2. 如果显示 **"✅ Connected"**，说明 WebRequest 配置正确
3. 如果显示 **"❌ Disconnected"**，检查白名单配置

### 方法 2：查看专家日志

1. 在 MT5 底部，点击 **工具箱 (Toolbox)** → **专家 (Experts)**
2. 查看日志输出

**✅ 成功日志：**
```
[GoldAI] ✅ Initial authentication successful
[GoldAI] 💓 Heartbeat sent successfully
[GoldAI] 📡 Poll: No new signals
```

**❌ 失败日志（WebRequest 被阻止）：**
```
[GoldAI] ❌ Auth failed: Cannot connect to https://your-api-domain.com/api/v1
[GoldAI] ⚠️ Check: 1) Internet connection 2) WebRequest whitelist 3) API URL
```

### 方法 3：测试网络连接

在专家日志中，如果看到 HTTP 0 错误，说明网络请求被阻止：

```
[GoldAI] ❌ Auth failed: HTTP 0
```

HTTP 0 表示请求未能发出，通常是 WebRequest 白名单未配置。

---

## 🛠️ 常见问题排查

### 问题 1：添加了 URL 但仍然无法连接

**可能原因：**
- MT5 未重启，配置未生效
- URL 格式错误（缺少 `https://`）
- URL 不完整（应包含域名，不包含路径）

**解决方法：**
1. 重启 MT5 终端
2. 确认 URL 格式：`https://your-api-domain.com`
3. 不要添加 `/api/v1` 等路径，只填域名

---

### 问题 2：多个 API 地址需要配置

**场景：** 有生产环境和测试环境

**解决方法：**
1. 在 WebRequest 白名单中，点击 **添加 (Add)**
2. 分别添加每个环境的地址：
   ```
   https://api.goldaitrader.com        (生产)
   https://test-api.goldaitrader.com   (测试)
   ```
3. MT5 允许添加多个 URL

---

### 问题 3：URL 配置错误如何修改

**解决方法：**
1. 工具 → 选项 → 专家顾问
2. 在 URL 列表中选中错误的地址
3. 点击 **编辑 (Edit)** 或 **删除 (Delete)**
4. 添加正确的地址
5. 保存并重启 MT5

---

### 问题 4：公司/机构网络有防火墙

**可能原因：**
- 公司防火墙阻止外部连接
- 需要代理服务器

**解决方法：**
1. 联系 IT 部门，确认 MT5 可以访问外部 HTTPS 地址
2. 如需代理，在 MT5 选项中配置代理服务器：
   - 工具 → 选项 → 服务器 (Servers)
   - 启用代理并配置地址

---

## 📋 WebRequest 配置检查清单

在部署 EA 前，请确认：

- [ ] 已打开 MT5 选项（Ctrl+O）
- [ ] 已切换到"专家顾问"标签页
- [ ] 已勾选"允许 WebRequest 访问以下 URL 列表"
- [ ] 已添加 API 服务器地址（`https://your-api-domain.com`）
- [ ] URL 格式正确（包含 `https://`，不包含路径）
- [ ] 已保存配置并重启 MT5
- [ ] EA 状态面板显示 "✅ Connected"
- [ ] 专家日志无 HTTP 0 错误

---

## 🔒 安全说明

### WebRequest 白名单的安全性

- **白名单机制：** MT5 只允许 EA 访问白名单中的 URL，其他地址会被阻止
- **EA 隔离：** 每个 EA 只能访问其被授权的 URL，无法随意访问网络
- **用户控制：** 用户可以随时在 MT5 选项中查看和修改白名单

### 最佳实践

1. **只添加必要的 URL：** 仅添加 EA 实际需要的 API 服务器
2. **使用 HTTPS：** 确保所有 URL 都使用 HTTPS 加密
3. **定期检查：** 定期审查白名单，移除不再使用的 URL
4. **不要共享配置：** 白名单配置包含您的 API 服务器地址，不要随意分享

---

## 📞 需要帮助？

如遇到 WebRequest 配置问题，请：

1. 截图 MT5 选项 → 专家顾问 页面
2. 截图 EA 专家日志中的错误信息
3. 联系服务提供商获取技术支持

---

## 📚 相关文档

- `INSTALL.md` - 完整安装指南
- `PARAMETERS.md` - 参数配置说明
- `SHADOW_TO_DEMO_CHECKLIST.md` - Shadow→Demo 切换检查清单
