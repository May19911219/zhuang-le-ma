# 进度

## 当前阶段

三个部分都已能运行，端到端流程已验证。

## 已完成

- 用 winget 安装 Python 3.12.10，服务端依赖安装完成
- FastAPI + SQLite：预置 17 个软件、版本缓存、安装方案、反馈、管理登录和选择次数
- 版本拉取已打到真实源：Node.js、Go、Git 都能返回远程版本；远程和 AI 都失败时用内置版本
- 没有 AI 时生成带中文注释、环境变量和验证命令的离线脚本；VS Code、IDEA 只给官方下载页
- 服务端测试 8 项通过
- 管理后台可登录、查看和修改方案、标记反馈、查看统计
- Electron 桌面端可搜索、选版本、渲染 Markdown、复制脚本，并在本机执行 PowerShell / Bash
- 用户流程已走通：输入「我想装 Git」→ 选中 2.56.0 → 生成方案 → 页面展示脚本和「一键安装」

## 进行中

- 无

## 问题及解决方案

- `python` 指向 Microsoft Store 占位程序：改用 `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`
- `%USERPROFILE%\.claude\settings.json` 不存在，没有写入 `AI_API_KEY`。离线方案可用；管理后台点「让 AI 重新生成」会提示「还没有配置 AI」。把配置文件放到该路径后重启服务即可
- `/api/software` 漏了 `Software` 导入，补上后测试通过
- Electron 预加载脚本实际输出为 `index.mjs`，已改加载路径
- 桌面端「去看看」按钮被挤成竖排，代码块撑出格子。搜索按钮改为不收缩，方案栏限制宽度后已再看过页面
- npm 11 默认不跑安装脚本，已批准 electron 和 esbuild 的安装脚本
