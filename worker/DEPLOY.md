# Scenario Task API 部署

该 API 用于把战略沙盘任务从浏览器本地存储同步到 Cloudflare Workers KV，并由 Worker 定时记录最新雷达状态。

## 1. 创建 KV Namespace

在 Cloudflare Dashboard 创建一个 Workers KV Namespace，例如：

`china-us-policy-radar-scenario-tasks`

把得到的 Namespace ID 填入根目录 `wrangler.toml` 的：

`id = "REPLACE_WITH_YOUR_KV_NAMESPACE_ID"`

不要把 API Token 写进代码。

## 2. 创建 Worker Token

生成一段随机长字符串作为 `SCENARIO_TASK_TOKEN`，并在 Worker 的 Secret 中保存。

## 3. GitHub Actions Secrets

在仓库 Secrets 中增加：

- `CLOUDFLARE_API_TOKEN`：Cloudflare API Token，至少具备 Workers 部署权限。
- `CLOUDFLARE_ACCOUNT_ID`：Cloudflare Account ID。

## 4. Worker Secret

部署后执行：

`wrangler secret put SCENARIO_TASK_TOKEN`

输入随机 Token。

## 5. 网页连接

部署成功后得到 Worker 地址，例如：

`https://china-us-policy-radar-scenario-tasks.<your-subdomain>.workers.dev`

打开战略沙盘的「历史推演任务 · 持久保存」，点击「设置服务器同步」，填入 Worker 地址和同一个 Token。

## 6. 安全边界

Token 只保存在浏览器 localStorage 和 Worker Secret，不写入网页源码、GitHub 仓库或 wrangler.toml。

API 默认要求 Authorization: Bearer <token>。没有 Token 不接受读写请求。
