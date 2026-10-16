import re

PLATFORM_LABELS = {"windows": "Windows", "macos": "macOS", "linux": "Linux"}

RECIPES: dict[str, dict] = {
    "mysql": {
        "winget": "Oracle.MySQL",
        "brew": "mysql",
        "apt": "mysql-server",
        "dnf": "mysql-server",
        "verify": {"windows": ["mysql --version"], "unix": ["mysql --version"]},
        "env_note": "安装程序会注册 mysql 命令。新开一个终端后 PATH 才会更新。",
    },
    "node": {
        "winget": "OpenJS.NodeJS.LTS",
        "brew": "node",
        "apt": "nodejs npm",
        "dnf": "nodejs npm",
        "url": "https://nodejs.org/dist/v{version}/node-v{version}-x64.msi",
        "verify": {"windows": ["node -v", "npm -v"], "unix": ["node -v", "npm -v"]},
        "path_dirs": [r"C:\Program Files\nodejs"],
        "env_note": "Node 安装目录会加入 Path，npm 全局包目录使用默认位置。",
    },
    "python": {
        "winget": "Python.Python.3.12",
        "brew": "python",
        "apt": "python3 python3-pip python3-venv",
        "dnf": "python3 python3-pip",
        "url": "https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe",
        "installer_args": "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0",
        "verify": {"windows": ["python --version", "pip --version"], "unix": ["python3 --version", "pip3 --version"]},
        "env_note": "Windows 安装时勾选加入 PATH。python 与 pip 都应能直接运行。",
    },
    "jdk": {
        "winget": "EclipseAdoptium.Temurin.21.JDK",
        "brew": "openjdk",
        "apt": "openjdk-21-jdk",
        "dnf": "java-21-openjdk-devel",
        "verify": {"windows": ["java -version"], "unix": ["java -version"]},
        "env_note": "需要设置 JAVA_HOME，并把 %JAVA_HOME%\\bin 或 $JAVA_HOME/bin 放进 PATH。",
        "special": "jdk",
    },
    "git": {
        "winget": "Git.Git",
        "brew": "git",
        "apt": "git",
        "dnf": "git",
        "verify": {"windows": ["git --version"], "unix": ["git --version"]},
        "path_dirs": [r"C:\Program Files\Git\cmd"],
        "env_note": "Git 的 cmd 目录需要在 Path 里。",
    },
    "maven": {
        "winget": "Apache.Maven",
        "brew": "maven",
        "apt": "maven",
        "dnf": "maven",
        "url": "https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/{version}/apache-maven-{version}-bin.zip",
        "verify": {"windows": ["mvn -version"], "unix": ["mvn -version"]},
        "env_note": "需要设置 MAVEN_HOME，并把 bin 目录加入 PATH。Maven 依赖 JAVA_HOME。",
        "special": "maven",
    },
    "redis": {
        "winget": "Redis.Redis",
        "brew": "redis",
        "apt": "redis-server",
        "dnf": "redis",
        "verify": {"windows": ["redis-server --version"], "unix": ["redis-server --version"]},
        "env_note": "Windows 若没有 winget 包，脚本会停下来并说明，不会偷偷改用别的数据库。",
    },
    "docker": {
        "winget": "Docker.DockerDesktop",
        "brew": "--cask docker",
        "apt": "docker.io",
        "dnf": "docker",
        "verify": {"windows": ["docker version"], "unix": ["docker --version"]},
        "env_note": "Docker Desktop 装完需要重新登录，命令才会出现在新的终端里。",
    },
    "nginx": {
        "winget": "Nginx.Nginx",
        "brew": "nginx",
        "apt": "nginx",
        "dnf": "nginx",
        "url": "https://nginx.org/download/nginx-{version}.zip",
        "verify": {"windows": ["nginx -v"], "unix": ["nginx -v"]},
        "env_note": "Windows 解压版需要把 nginx 目录加入 Path。",
        "special": "nginx",
    },
    "go": {
        "winget": "GoLang.Go",
        "brew": "go",
        "apt": "golang-go",
        "dnf": "golang",
        "url": "https://go.dev/dl/go{version}.windows-amd64.msi",
        "verify": {"windows": ["go version"], "unix": ["go version"]},
        "path_dirs": [r"C:\Program Files\Go\bin"],
        "env_note": "设置 GOROOT 为安装目录，GOPATH 默认为用户目录下的 go，并把两者的 bin 加入 Path。",
        "special": "go",
    },
    "rust": {
        "winget": "Rustlang.Rustup",
        "brew": "rustup",
        "apt": "",
        "dnf": "",
        "verify": {"windows": ["rustc --version", "cargo --version"], "unix": ["rustc --version", "cargo --version"]},
        "env_note": "rustup 会把工具链装到用户目录，并把 cargo bin 加入 Path。",
        "special": "rust",
    },
    "mongodb": {
        "winget": "MongoDB.Server",
        "brew": "mongodb-community",
        "apt": "mongodb",
        "dnf": "mongodb",
        "verify": {"windows": ["mongod --version"], "unix": ["mongod --version"]},
        "env_note": "把 MongoDB 的 bin 目录加入 Path。数据目录默认由安装包创建。",
    },
    "postgresql": {
        "winget": "PostgreSQL.PostgreSQL",
        "brew": "postgresql",
        "apt": "postgresql",
        "dnf": "postgresql-server",
        "verify": {"windows": ["psql --version"], "unix": ["psql --version"]},
        "env_note": "Windows 安装包通常把 bin 放在 Program Files\\PostgreSQL\\版本号\\bin，脚本会尝试把它加入 Path。",
        "special": "postgres",
    },
    "homebrew": {
        "special": "homebrew",
        "verify": {"windows": [], "unix": ["brew --version"]},
        "env_note": "Homebrew 主要用于 macOS 和 Linux。安装脚本会把 brew 可执行文件所在目录写进 shell 配置。",
    },
    "nvm": {
        "winget": "CoreyButler.NVMforWindows",
        "verify": {"windows": ["nvm version"], "unix": ["bash -lc 'source ~/.nvm/nvm.sh && nvm --version'"]},
        "env_note": "Windows 安装的是 nvm-windows。macOS 和 Linux 安装官方 nvm，并写入 shell 配置。",
        "special": "nvm",
    },
}


def platform_label(platform: str) -> str:
    """返回平台的展示名称。"""
    return PLATFORM_LABELS.get(platform, platform)


def shell_for(platform: str) -> str:
    """按平台选择脚本解释器。"""
    return "powershell" if platform == "windows" else "bash"


def _fill(template: str, values: dict[str, str]) -> str:
    """替换模板中的具名占位符，保留脚本里的其他花括号。"""
    text = template
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def _ps_quote(value: str) -> str:
    """转义 PowerShell 单引号字符串。"""
    return value.replace("'", "''")


def render_windows(slug: str, version: str) -> str:
    """生成带中文注释的 Windows PowerShell 安装脚本。"""
    recipe = RECIPES.get(slug, {})
    special = recipe.get("special")
    if special == "homebrew":
        return "\n".join(
            [
                "# Homebrew 不支持作为 Windows 的包管理器使用",
                "Write-Host 'Homebrew 请在 macOS 或 Linux 上安装。Windows 请改用 winget。'",
                "exit 1",
            ]
        )
    lines = [
        f"# 安装 {slug} {version}",
        "# 先尝试 winget，失败后再按官方包安装",
        '$ErrorActionPreference = "Stop"',
        f"$Version = '{_ps_quote(version)}'",
        "$installed = $false",
    ]
    winget_id = recipe.get("winget", "")
    if winget_id:
        lines.extend(
            [
                "if (Get-Command winget -ErrorAction SilentlyContinue) {",
                "  # 使用 winget 安装指定版本；版本在源里不存在时会进入后面的补救",
                f"  winget install --id {winget_id} -v $Version --accept-package-agreements --accept-source-agreements",
                "  if ($LASTEXITCODE -eq 0) { $installed = $true }",
                "}",
            ]
        )
    url = recipe.get("url", "")
    if url:
        concrete = url.replace("{version}", version)
        if concrete.endswith(".msi"):
            lines.extend(
                [
                    "if (-not $installed) {",
                    "  # 下载官方 MSI 并静默安装",
                    f"  $pkg = Join-Path $env:TEMP 'zhuang-setup.msi'",
                    f"  Invoke-WebRequest -Uri '{concrete}' -OutFile $pkg",
                    "  Start-Process msiexec.exe -ArgumentList '/i', $pkg, '/qn', '/norestart' -Wait",
                    "  $installed = $true",
                    "}",
                ]
            )
        elif concrete.endswith(".exe"):
            args = recipe.get("installer_args", "/quiet /norestart")
            lines.extend(
                [
                    "if (-not $installed) {",
                    "  # 下载官方安装包并静默安装",
                    f"  $pkg = Join-Path $env:TEMP 'zhuang-setup.exe'",
                    f"  Invoke-WebRequest -Uri '{concrete}' -OutFile $pkg",
                    f"  Start-Process $pkg -ArgumentList '{args}' -Wait",
                    "  $installed = $true",
                    "}",
                ]
            )
        elif concrete.endswith(".zip"):
            lines.extend(
                [
                    "if (-not $installed) {",
                    "  # 下载压缩包并解压到 C:\\Tools",
                    "  $dest = 'C:\\Tools'",
                    "  New-Item -ItemType Directory -Force -Path $dest | Out-Null",
                    "  $pkg = Join-Path $env:TEMP 'zhuang-setup.zip'",
                    f"  Invoke-WebRequest -Uri '{concrete}' -OutFile $pkg",
                    "  Expand-Archive -Path $pkg -DestinationPath $dest -Force",
                    "  $installed = $true",
                    "}",
                ]
            )
    lines.extend(_windows_env(slug, version, recipe))
    verify_commands = recipe.get("verify", {}).get("windows") or [f"{slug} --version"]
    lines.append("# 让当前会话看到刚写好的环境变量")
    lines.append(
        '$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")'
    )
    for command in verify_commands:
        lines.append(f'# 验证命令：{command}')
        lines.append(f"Write-Host '验证: {command}'")
        lines.append(command)
        lines.append(f"if ($LASTEXITCODE -ne 0) {{ throw '验证失败: {command}' }}")
    lines.append("Write-Host '安装步骤已执行，请再开一个新终端复验上面的命令。'")
    return "\n".join(lines)


def _windows_env(slug: str, version: str, recipe: dict) -> list[str]:
    """生成 Windows 环境变量配置片段。"""
    lines = ["# 配置环境变量。写机器级变量需要管理员权限，失败时请用管理员 PowerShell 重跑。"]
    for directory in recipe.get("path_dirs") or []:
        lines.extend(
            [
                f"$dir = '{directory}'",
                "if (Test-Path $dir) {",
                '  $machinePath = [Environment]::GetEnvironmentVariable("Path","Machine")',
                '  if ($machinePath -notlike "*$dir*") {',
                '    [Environment]::SetEnvironmentVariable("Path", "$machinePath;$dir", "Machine")',
                "  }",
                '  if ($env:Path -notlike "*$dir*") { $env:Path = "$dir;" + $env:Path }',
                "} else {",
                "  Write-Host \"目录还不存在，跳过 Path：$dir\"",
                "}",
            ]
        )
    special = recipe.get("special")
    if special == "jdk":
        lines.extend(
            [
                "# 查找 JDK 目录并写入 JAVA_HOME",
                '$roots = @("C:\\Program Files\\Eclipse Adoptium", "C:\\Program Files\\Java", "C:\\Program Files\\Microsoft")',
                "$jdk = $null",
                "foreach ($root in $roots) {",
                "  if (Test-Path $root) {",
                "    $jdk = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'jdk*' } | Sort-Object Name -Descending | Select-Object -First 1",
                "    if ($jdk) { break }",
                "  }",
                "}",
                "if ($jdk) {",
                '  [Environment]::SetEnvironmentVariable("JAVA_HOME", $jdk.FullName, "Machine")',
                "  $env:JAVA_HOME = $jdk.FullName",
                '  $env:Path = "$($jdk.FullName)\\bin;" + $env:Path',
                "} else {",
                "  Write-Host '没有找到 JDK 目录，请安装完成后再设置 JAVA_HOME'",
                "}",
            ]
        )
    if special == "maven":
        home = f"C:\\Tools\\apache-maven-{version}"
        lines.extend(
            [
                f"$mavenHome = '{home}'",
                "if (Test-Path $mavenHome) {",
                '  [Environment]::SetEnvironmentVariable("MAVEN_HOME", $mavenHome, "Machine")',
                "  $env:MAVEN_HOME = $mavenHome",
                '  $env:Path = "$mavenHome\\bin;" + $env:Path',
                "}",
            ]
        )
    if special == "go":
        lines.extend(
            [
                "$goRoot = 'C:\\Program Files\\Go'",
                "if (Test-Path $goRoot) {",
                '  [Environment]::SetEnvironmentVariable("GOROOT", $goRoot, "Machine")',
                "  $goPath = Join-Path $env:USERPROFILE 'go'",
                '  [Environment]::SetEnvironmentVariable("GOPATH", $goPath, "User")',
                "  $env:GOROOT = $goRoot",
                "  $env:GOPATH = $goPath",
                '  $env:Path = "$goRoot\\bin;$goPath\\bin;" + $env:Path',
                "}",
            ]
        )
    if special == "nginx":
        lines.extend(
            [
                "$nginxDir = Get-ChildItem 'C:\\Tools' -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'nginx-*' } | Sort-Object Name -Descending | Select-Object -First 1",
                "if ($nginxDir) {",
                '  $env:Path = "$($nginxDir.FullName);" + $env:Path',
                "}",
            ]
        )
    if special == "postgres":
        lines.extend(
            [
                "$pg = Get-ChildItem 'C:\\Program Files\\PostgreSQL' -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1",
                "if ($pg) {",
                "  $bin = Join-Path $pg.FullName 'bin'",
                '  if ($env:Path -notlike "*$bin*") { $env:Path = "$bin;" + $env:Path }',
                "}",
            ]
        )
    if special == "rust":
        lines.extend(
            [
                "# 用 rustup 安装指定稳定工具链",
                "$rustup = Join-Path $env:USERPROFILE '.cargo\\bin\\rustup.exe'",
                "if (-not (Test-Path $rustup)) {",
                "  $init = Join-Path $env:TEMP 'rustup-init.exe'",
                "  Invoke-WebRequest -Uri 'https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe' -OutFile $init",
                "  Start-Process $init -ArgumentList '-y','--default-toolchain',$Version -Wait",
                "}",
                '$env:Path = "$env:USERPROFILE\\.cargo\\bin;" + $env:Path',
                "rustup default $Version",
            ]
        )
    if special == "nvm" and slug == "nvm":
        lines.append("# nvm-windows 会自己注册 nvm 命令，重开终端后生效")
    return lines


def render_unix(slug: str, version: str, platform: str) -> str:
    """生成带中文注释的 Bash 安装脚本。"""
    recipe = RECIPES.get(slug, {})
    special = recipe.get("special")
    if special == "homebrew":
        return "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"# 安装 Homebrew（记录版本 {version}，官方脚本会安装当前发布版）",
                '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                "# 把 brew 加进当前用户的 shell 配置",
                'if [[ -x /opt/homebrew/bin/brew ]]; then',
                "  echo 'eval \"$(/opt/homebrew/bin/brew shellenv)\"' >> \"$HOME/.zprofile\"",
                "  eval \"$(/opt/homebrew/bin/brew shellenv)\"",
                "elif [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then",
                "  echo 'eval \"$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)\"' >> \"$HOME/.bashrc\"",
                "  eval \"$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)\"",
                "fi",
                "brew --version",
            ]
        )
    if special == "nvm":
        return "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"# 安装 nvm {version}",
                f'curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/v{version}/install.sh" | bash',
                "# 当前会话加载 nvm",
                'export NVM_DIR="$HOME/.nvm"',
                '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"',
                "nvm --version",
            ]
        )
    brew = recipe.get("brew", slug)
    apt = recipe.get("apt") or slug
    dnf = recipe.get("dnf") or slug
    verify = recipe.get("verify", {}).get("unix") or [f"{slug} --version"]
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"# 安装 {slug} {version}",
        f'VERSION="{version}"',
        "# 包管理器不一定提供完全相同的小版本，装完后用验证命令核对",
    ]
    if platform == "macos":
        lines.extend(
            [
                "if ! command -v brew >/dev/null 2>&1; then",
                "  echo '没有找到 Homebrew。请先安装 Homebrew，再重跑这个脚本。' >&2",
                "  exit 1",
                "fi",
                f"brew install {brew}",
            ]
        )
    else:
        lines.extend(
            [
                "if command -v apt-get >/dev/null 2>&1; then",
                "  sudo apt-get update",
                f"  sudo apt-get install -y {apt}",
                "elif command -v dnf >/dev/null 2>&1; then",
                f"  sudo dnf install -y {dnf}",
                "else",
                "  echo '没有找到 apt-get 或 dnf。' >&2",
                "  exit 1",
                "fi",
            ]
        )
    if special == "jdk":
        lines.extend(
            [
                "# 尝试把 JAVA_HOME 写到当前用户配置",
                "if [[ -d /usr/lib/jvm ]]; then",
                "  JAVA_HOME_DETECTED=$(echo /usr/lib/jvm/* | awk '{print $1}')",
                '  if [[ -n "${JAVA_HOME_DETECTED}" ]]; then',
                "    echo \"export JAVA_HOME=${JAVA_HOME_DETECTED}\" >> \"$HOME/.bashrc\"",
                '    export JAVA_HOME="${JAVA_HOME_DETECTED}"',
                '    export PATH="$JAVA_HOME/bin:$PATH"',
                "  fi",
                "fi",
            ]
        )
    if special == "go":
        lines.extend(
            [
                "# 设置 Go 常用环境变量",
                'export GOPATH="$HOME/go"',
                'export PATH="/usr/local/go/bin:$GOPATH/bin:$PATH"',
                "echo 'export GOPATH=\"$HOME/go\"' >> \"$HOME/.bashrc\"",
                "echo 'export PATH=\"/usr/local/go/bin:$GOPATH/bin:$PATH\"' >> \"$HOME/.bashrc\"",
            ]
        )
    if special == "rust":
        lines.extend(
            [
                "# 使用 rustup 安装指定工具链",
                "curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs | sh -s -- -y --default-toolchain \"$VERSION\"",
                '. "$HOME/.cargo/env"',
            ]
        )
    for command in verify:
        lines.append(f"echo '验证: {command}'")
        lines.append(command)
    lines.append("echo '安装步骤已执行。请打开新的终端再跑一次验证命令。'")
    return "\n".join(lines)


def render_script(slug: str, version: str, platform: str) -> str:
    """按平台生成安装脚本。"""
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", version):
        raise ValueError("版本号格式不正确")
    if platform == "windows":
        return render_windows(slug, version)
    return render_unix(slug, version, platform)


def fallback_markdown(name: str, slug: str, version: str, platform: str, install_type: str, official_url: str) -> tuple[str, str, str]:
    """在没有 AI 结果时组装安装说明、脚本和解释器类型。"""
    label = platform_label(platform)
    if install_type == "official_link":
        markdown = "\n".join(
            [
                f"# 安装 {name} {version}（{label}）",
                "",
                f"官方下载页：{official_url}",
                "",
                "## 脚本运行说明",
                "",
                "这个软件使用官方安装包，不提供一键脚本。",
                f"打开上面的官方下载页，选择 {label} 对应的 {version} 安装包，按安装向导完成安装。",
                "",
                "## 执行后建议",
                "",
                "安装结束后重新打开终端或开始菜单，确认命令或应用图标已经出现。",
                "如果页面上的版本号和这里不一致，以官方下载页当前提供的稳定包为准。",
                "",
                "## 常见问题",
                "",
                "下载被拦截时，换系统浏览器再打开同一个官方地址。",
                "装完找不到程序时，先注销并重新登录，再检查开始菜单或应用程序目录。",
            ]
        )
        return markdown, "", ""
    script = render_script(slug, version, platform)
    fence = "powershell" if platform == "windows" else "bash"
    recipe = RECIPES.get(slug, {})
    env_note = recipe.get("env_note", "脚本会把可执行文件所在目录加入 PATH。")
    markdown = "\n".join(
        [
            f"# 安装 {name} {version}（{label}）",
            "",
            "## 一键安装脚本",
            "",
            f"```{fence}",
            script,
            "```",
            "",
            "## 脚本运行说明",
            "",
            "Windows 用 PowerShell 执行，macOS 和 Linux 用 Bash 执行。",
            "脚本先调用系统包管理器；失败时再下载官方安装包。",
            env_note,
            "看到「验证」字样的命令退出码不为 0 时，安装没有完成。",
            "",
            "## 执行后建议",
            "",
            "关掉当前终端，新开一个窗口，再手动跑一次脚本末尾的验证命令。",
            "确认输出版本与所选版本一致，或至少属于同一稳定通道。",
            "",
            "## 常见问题",
            "",
            "提示拒绝访问或需要管理员时，用管理员 PowerShell，或在 macOS / Linux 上允许 sudo 后重跑。",
            "提示命令找不到时，先看环境变量有没有写上，再开一个新终端。不要在同一个旧窗口里判断失败。",
            "包管理器没有这个精确版本时，脚本会改走官方安装包；官方包也失败时，保留终端里的原报错。",
        ]
    )
    return markdown, script, shell_for(platform)
