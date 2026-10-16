import { spawn, type ChildProcess } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { closeSync, openSync, readSync, statSync } from 'node:fs'
import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { app, BrowserWindow, ipcMain, shell } from 'electron'

type InstallRequest = {
  script: string
  shell: 'powershell' | 'bash'
  elevate: boolean
}

/** 创建桌面主窗口。 */
function createWindow(): void {
  const win = new BrowserWindow({
    width: 1180,
    height: 820,
    minWidth: 960,
    minHeight: 680,
    title: '装了吗',
    backgroundColor: '#E4EEF2',
    webPreferences: {
      preload: join(__dirname, '../preload/index.mjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    void win.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    void win.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

/** 把安装脚本写到临时目录。 */
async function writeScript(script: string, shellName: InstallRequest['shell']): Promise<{ id: string; file: string; logFile: string; dir: string }> {
  const id = randomUUID()
  const dir = join(app.getPath('temp'), 'zhuang-le-ma')
  await mkdir(dir, { recursive: true })
  const ext = shellName === 'powershell' ? 'ps1' : 'sh'
  const file = join(dir, `${id}.${ext}`)
  const logFile = join(dir, `${id}.log`)
  const body = shellName === 'powershell' ? `\uFEFF${script}` : script
  await writeFile(file, body, 'utf8')
  return { id, file, logFile, dir }
}

/** 轮询日志文件，把新增内容推给界面。 */
function tailLog(logFile: string, child: ChildProcess, send: (chunk: string) => void): void {
  let offset = 0
  const readNew = (): void => {
    try {
      const size = statSync(logFile).size
      if (size <= offset) return
      const length = size - offset
      const buffer = Buffer.alloc(length)
      const fd = openSync(logFile, 'r')
      readSync(fd, buffer, 0, length, offset)
      closeSync(fd)
      offset = size
      send(buffer.toString('utf8'))
    } catch {
      // 提权进程还没创建日志文件
    }
  }
  const timer = setInterval(readNew, 400)
  child.on('exit', () => {
    clearInterval(timer)
    readNew()
  })
}

/** 按平台启动脚本进程，可选管理员权限。 */
function spawnInstall(payload: InstallRequest, paths: { file: string; logFile: string; dir: string; id: string }, emit: (stream: 'stdout' | 'stderr' | 'exit', chunk: string) => void): void {
  if (payload.elevate && process.platform === 'win32') {
    const wrapper = join(paths.dir, `${paths.id}-elevate.ps1`)
    const wrapperText = [
      "$ErrorActionPreference = 'Continue'",
      'try {',
      `  & '${paths.file.replace(/'/g, "''")}' *>&1 | Tee-Object -FilePath '${paths.logFile.replace(/'/g, "''")}'`,
      '  exit $LASTEXITCODE',
      '} catch {',
      `  $_ | Out-File -FilePath '${paths.logFile.replace(/'/g, "''")}' -Append -Encoding utf8`,
      '  exit 1',
      '}',
    ].join('\n')
    void writeFile(wrapper, `\uFEFF${wrapperText}`, 'utf8').then(() => {
      const child = spawn(
        'powershell.exe',
        [
          '-NoProfile',
          '-Command',
          `Start-Process -FilePath powershell.exe -Verb RunAs -Wait -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','${wrapper}'`,
        ],
        { windowsHide: true },
      )
      tailLog(paths.logFile, child, (chunk) => emit('stdout', chunk))
      child.stderr.on('data', (chunk: Buffer) => emit('stderr', chunk.toString('utf8')))
      child.on('exit', (code) => emit('exit', String(code ?? 0)))
      child.on('error', (error) => emit('stderr', error.message))
    })
    return
  }

  if (payload.elevate && process.platform === 'darwin') {
    const child = spawn('osascript', [
      '-e',
      `do shell script "bash ${JSON.stringify(paths.file)} > ${JSON.stringify(paths.logFile)} 2>&1" with administrator privileges`,
    ])
    tailLog(paths.logFile, child, (chunk) => emit('stdout', chunk))
    child.on('exit', (code) => emit('exit', String(code ?? 0)))
    child.on('error', (error) => emit('stderr', error.message))
    return
  }

  const command = payload.shell === 'powershell' ? 'powershell.exe' : 'bash'
  const args = payload.shell === 'powershell' ? ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', paths.file] : [paths.file]
  const child = spawn(command, args, { windowsHide: true })
  child.stdout.on('data', (chunk: Buffer) => emit('stdout', chunk.toString('utf8')))
  child.stderr.on('data', (chunk: Buffer) => emit('stderr', chunk.toString('utf8')))
  child.on('exit', (code) => emit('exit', String(code ?? 0)))
  child.on('error', (error) => emit('stderr', error.message))
}

app.whenReady().then(() => {
  ipcMain.handle('app:platform', () => process.platform)
  ipcMain.handle('shell:open', async (_event, url: string) => {
    if (!/^https?:\/\//i.test(url)) {
      throw new Error('只打开 http 链接')
    }
    await shell.openExternal(url)
  })
  ipcMain.handle('install:run', async (event, payload: InstallRequest) => {
    const paths = await writeScript(payload.script, payload.shell)
    const emit = (stream: 'stdout' | 'stderr' | 'exit', chunk: string): void => {
      if (!event.sender.isDestroyed()) {
        event.sender.send('install:log', { id: paths.id, stream, chunk })
      }
    }
    spawnInstall(payload, paths, emit)
    return { id: paths.id }
  })
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
