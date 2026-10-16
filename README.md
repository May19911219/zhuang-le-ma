# 装了吗

今天你装了吗？给学编程的同学查版本、生成安装方案，并在桌面应用里执行脚本。

## 启动

三个进程都要开。API 地址是 `http://127.0.0.1:8765`。

```powershell
# 服务端
cd server
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8765

# 管理后台
cd admin
npm install
npm run dev

# 桌面端
cd desktop
npm install
npm run dev
```

管理密码默认是 `zhuang-le-ma`，写在 `server/.env` 的 `ADMIN_PASSWORD`。后台地址是 `http://127.0.0.1:5174`。

## AI

启动服务时会读取 `%USERPROFILE%\.claude\settings.json` 里的 `env.ANTHROPIC_AUTH_TOKEN` 和 `env.ANTHROPIC_BASE_URL`，并写入 `server/.env` 的 `AI_API_KEY`、`AI_BASE_URL`。接口使用 OpenAI 兼容的 `/v1/chat/completions`。模型名用 `AI_MODEL`，默认 `claude-sonnet-4-5`。

没有这份配置时，预置软件仍会使用离线安装说明。管理后台里的「让 AI 重新生成」会提示还没有配置 AI。
