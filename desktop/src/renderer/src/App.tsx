import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input, Textarea } from '@/components/ui/input'
import { CopyScriptButton, PlanMarkdown } from '@/components/PlanMarkdown'
import {
  createPlan,
  fetchSoftware,
  fetchVersions,
  parseQuery,
  sendFeedback,
  type Plan,
  type Software,
  type VersionItem,
} from '@/lib/api'

type PlatformName = 'windows' | 'macos' | 'linux'

const PLATFORM_OPTIONS: { id: PlatformName; label: string }[] = [
  { id: 'windows', label: 'Windows' },
  { id: 'macos', label: 'macOS' },
  { id: 'linux', label: 'Linux' },
]

/** 把 Electron 的平台名换成安装方案使用的名称。 */
function mapPlatform(value: string): PlatformName {
  if (value === 'darwin' || value === 'macos') return 'macos'
  if (value === 'linux') return 'linux'
  return 'windows'
}

/** 判断日志里是否出现了需要提权的报错。 */
function needsAdmin(text: string): boolean {
  return /拒绝访问|需要管理员|Access is denied|requires elevation|requested operation requires/i.test(text)
}

/** 装了吗桌面主界面。 */
export function App() {
  const [platform, setPlatform] = useState<PlatformName>('windows')
  const [query, setQuery] = useState('')
  const [catalog, setCatalog] = useState<Software[]>([])
  const [software, setSoftware] = useState<Software | null>(null)
  const [versions, setVersions] = useState<VersionItem[]>([])
  const [versionSource, setVersionSource] = useState('')
  const [version, setVersion] = useState('')
  const [plan, setPlan] = useState<Plan | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [log, setLog] = useState('')
  const [running, setRunning] = useState(false)
  const [askAdmin, setAskAdmin] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [feedbackNote, setFeedbackNote] = useState('')

  useEffect(() => {
    void fetchSoftware()
      .then(setCatalog)
      .catch(() => setError('服务没连上。先在 server 目录启动 API。'))
    void window.desktop?.getPlatform().then((value) => setPlatform(mapPlatform(value)))
  }, [])

  /** 载入所选软件的版本，并默认选中最新稳定版。 */
  async function loadVersions(item: Software, nextPlatform: PlatformName): Promise<void> {
    setBusy('正在查版本')
    setError('')
    setPlan(null)
    setSoftware(item)
    try {
      const result = await fetchVersions(item.slug, nextPlatform)
      setVersions(result.versions)
      setVersionSource(result.source)
      const latest = result.versions.find((entry) => entry.isLatestStable) ?? result.versions[0]
      setVersion(latest?.version ?? '')
    } catch (reason) {
      setVersions([])
      setVersion('')
      setError(reason instanceof Error ? reason.message : '版本没有查到')
    } finally {
      setBusy('')
    }
  }

  /** 根据输入提炼软件并打开版本列表。 */
  async function onSearch(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (!query.trim()) return
    setBusy('正在辨认软件')
    setError('')
    try {
      const parsed = await parseQuery(query.trim())
      await loadVersions(parsed, platform)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '没有辨认出来')
    } finally {
      setBusy('')
    }
  }

  /** 按当前软件、版本和平台生成安装方案。 */
  async function onGenerate(): Promise<void> {
    if (!software || !version) return
    setBusy('正在写安装方案')
    setError('')
    try {
      const next = await createPlan(software.slug, version, platform)
      setPlan(next)
      setFeedbackNote('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '方案没有生成')
    } finally {
      setBusy('')
    }
  }

  /** 在本机执行脚本，或打开官方下载页。 */
  async function onInstall(elevate: boolean): Promise<void> {
    if (!plan) return
    if (plan.installType === 'official_link') {
      const url = plan.officialUrl
      if (window.desktop) {
        await window.desktop.openExternal(url)
      } else {
        window.open(url, '_blank', 'noopener')
      }
      return
    }
    if (!window.desktop) {
      setError('一键安装只能在桌面应用里执行。你仍然可以复制脚本。')
      return
    }
    if (!plan.script) {
      setError('这份方案没有脚本。')
      return
    }
    setRunning(true)
    setAskAdmin(false)
    setLog(elevate ? '正在请求管理员权限…\n' : '')
    let activeId = ''
    const off = window.desktop.onInstallLog((entry) => {
      if (!activeId) activeId = entry.id
      if (entry.id !== activeId) return
      if (entry.stream === 'exit') {
        setLog((current) => `${current}\n进程结束，退出码 ${entry.chunk}\n`)
        setRunning(false)
        off()
        return
      }
      setLog((current) => {
        const next = current + entry.chunk
        if (needsAdmin(next)) setAskAdmin(true)
        return next
      })
    })
    try {
      const shell = plan.scriptShell === 'bash' ? 'bash' : 'powershell'
      const started = await window.desktop.runInstall({
        script: plan.script,
        shell,
        elevate,
      })
      activeId = started.id
    } catch (reason) {
      off()
      setRunning(false)
      setError(reason instanceof Error ? reason.message : '脚本没有启动')
    }
  }

  /** 提交这条方案有没有帮上忙。 */
  async function onFeedback(verdict: 'valid' | 'invalid'): Promise<void> {
    if (!plan) return
    try {
      await sendFeedback(plan.id, verdict, feedback)
      setFeedbackNote(verdict === 'valid' ? '已记成有效' : '已记成无效')
      setFeedback('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '反馈没送出去')
    }
  }

  return (
    <main className="page">
      <header className="top">
        <div className="slogan">
          <p className="brand">装了吗</p>
          <h1>今天你装了吗？</h1>
        </div>
        <div className="platforms" role="group" aria-label="平台">
          {PLATFORM_OPTIONS.map((item) => (
            <Button
              key={item.id}
              type="button"
              size="sm"
              variant="quiet"
              aria-pressed={platform === item.id}
              onClick={() => {
                setPlatform(item.id)
                if (software) void loadVersions(software, item.id)
              }}
            >
              {item.label}
            </Button>
          ))}
        </div>
      </header>

      <form className="search" onSubmit={(event) => void onSearch(event)}>
        <Input
          value={query}
          placeholder="我想装 MySQL"
          aria-label="想装的软件"
          onChange={(event) => setQuery(event.target.value)}
        />
        <Button type="submit" variant="sticker" disabled={Boolean(busy)}>
          去看看
        </Button>
      </form>

      <div className="stickers">
        {catalog.map((item) => (
          <button
            key={item.slug}
            type="button"
            className="sticker"
            aria-pressed={software?.slug === item.slug}
            onClick={() => void loadVersions(item, platform)}
          >
            {item.name}
          </button>
        ))}
      </div>

      {busy ? <p className="note">{busy}</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <section className="workspace">
        <aside className="versions">
          <h2>{software ? software.name : '版本'}</h2>
          {versionSource ? <p className="note">版本来源：{versionSource}</p> : null}
          <div className="version-list">
            {versions.map((item) => (
              <button
                key={item.version}
                type="button"
                aria-pressed={version === item.version}
                onClick={() => setVersion(item.version)}
              >
                {item.version}
                {item.isLatestStable ? '  最新稳定版' : ''}
              </button>
            ))}
          </div>
          <div className="actions">
            <Button type="button" variant="sticker" disabled={!version || Boolean(busy)} onClick={() => void onGenerate()}>
              生成安装方案
            </Button>
          </div>
        </aside>

        <article className="notebook">
          {plan ? (
            <>
              <PlanMarkdown markdown={plan.markdown} />
              {plan.generatedBy === 'fallback' ? <p className="note">这张安装单是离线写的。接上 AI 后会按同一软件和版本重写。</p> : null}
              <div className="actions">
                {plan.script ? <CopyScriptButton script={plan.script} /> : null}
                <Button type="button" disabled={running} onClick={() => void onInstall(false)}>
                  {plan.installType === 'official_link' ? '打开官方下载页' : '一键安装'}
                </Button>
                {askAdmin && plan.installType === 'script' ? (
                  <Button type="button" variant="danger" disabled={running} onClick={() => void onInstall(true)}>
                    以管理员重试
                  </Button>
                ) : null}
              </div>
            </>
          ) : (
            <p>先写你想装的软件，或者点下面一张贴纸。选好版本后再生成安装方案。</p>
          )}
        </article>
      </section>

      <section className="log">
        <h2>安装日志</h2>
        <pre>{log || '还没有执行脚本。'}</pre>
      </section>

      <section className="feedback">
        <h2>这张方案有用吗</h2>
        <Textarea
          value={feedback}
          placeholder="可以写卡在哪一步，也可以留空"
          onChange={(event) => setFeedback(event.target.value)}
        />
        <div className="actions">
          <Button type="button" variant="good" size="sm" disabled={!plan} onClick={() => void onFeedback('valid')}>
            有效
          </Button>
          <Button type="button" variant="danger" size="sm" disabled={!plan} onClick={() => void onFeedback('invalid')}>
            无效
          </Button>
          {feedbackNote ? <span className="note">{feedbackNote}</span> : null}
        </div>
      </section>
    </main>
  )
}
