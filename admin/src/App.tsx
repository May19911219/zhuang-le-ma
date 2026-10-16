import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  deletePlan,
  fetchFeedback,
  fetchPlans,
  fetchStats,
  login,
  readToken,
  regeneratePlan,
  savePlan,
  updateFeedback,
  writeToken,
  type AdminFeedback,
  type AdminPlan,
  type AdminStat,
} from '@/lib/api'

type TabName = 'plans' | 'feedback' | 'stats'

/** 管理后台：登录、方案、反馈和统计。 */
export function App() {
  const [authed, setAuthed] = useState(Boolean(readToken()))
  const [password, setPassword] = useState('')
  const [tab, setTab] = useState<TabName>('plans')
  const [error, setError] = useState('')
  const [plans, setPlans] = useState<AdminPlan[]>([])
  const [feedback, setFeedback] = useState<AdminFeedback[]>([])
  const [stats, setStats] = useState<AdminStat[]>([])
  const [selected, setSelected] = useState<AdminPlan | null>(null)
  const [markdown, setMarkdown] = useState('')
  const [script, setScript] = useState('')
  const [note, setNote] = useState('')

  /** 按当前页签拉取数据。 */
  async function load(next: TabName): Promise<void> {
    setError('')
    if (next === 'plans') {
      const rows = await fetchPlans()
      setPlans(rows)
    } else if (next === 'feedback') {
      setFeedback(await fetchFeedback())
    } else {
      setStats(await fetchStats())
    }
  }

  useEffect(() => {
    if (!authed) return
    void load(tab).catch((reason: unknown) => {
      const message = reason instanceof Error ? reason.message : '加载失败'
      if (message.includes('登录')) {
        writeToken('')
        setAuthed(false)
      }
      setError(message)
    })
  }, [authed, tab])

  /** 提交密码并进入后台。 */
  async function onLogin(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    setError('')
    try {
      await login(password)
      setAuthed(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '登录失败')
    }
  }

  /** 切换页签时清掉上一页留下的提示。 */
  function switchTab(next: TabName): void {
    setNote('')
    setError('')
    setTab(next)
  }

  /** 打开一份方案到编辑区。 */
  function openPlan(plan: AdminPlan): void {
    setSelected(plan)
    setMarkdown(plan.markdown)
    setScript(plan.script)
    setNote('')
  }

  return (
    <main className="wrap">
      <div className="stamp">
        <h1>装了吗 · 后台</h1>
      </div>
      {!authed ? (
        <form className="login" onSubmit={(event) => void onLogin(event)}>
          <input
            type="password"
            value={password}
            aria-label="管理密码"
            placeholder="管理密码"
            onChange={(event) => setPassword(event.target.value)}
          />
          <Button type="submit" variant="sticker">
            登录
          </Button>
          {error ? <p className="error">{error}</p> : null}
        </form>
      ) : (
        <>
          <div className="tabs">
            <Button type="button" variant="quiet" aria-pressed={tab === 'plans'} onClick={() => switchTab('plans')}>
              方案
            </Button>
            <Button type="button" variant="quiet" aria-pressed={tab === 'feedback'} onClick={() => switchTab('feedback')}>
              反馈
            </Button>
            <Button type="button" variant="quiet" aria-pressed={tab === 'stats'} onClick={() => switchTab('stats')}>
              统计
            </Button>
            <Button
              type="button"
              variant="quiet"
              onClick={() => {
                writeToken('')
                setAuthed(false)
              }}
            >
              退出
            </Button>
          </div>
          {error ? <p className="error">{error}</p> : null}
          {note ? <p>{note}</p> : null}
          {tab === 'plans' ? (
            <section className="panel">
              <table>
                <thead>
                  <tr>
                    <th>软件</th>
                    <th>版本</th>
                    <th>平台</th>
                    <th>来源</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {plans.map((plan) => (
                    <tr key={plan.id}>
                      <td>{plan.software.name}</td>
                      <td>{plan.version}</td>
                      <td>{plan.platform}</td>
                      <td>{plan.generatedBy}</td>
                      <td>
                        <Button type="button" size="sm" variant="quiet" onClick={() => openPlan(plan)}>
                          查看
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {selected ? (
                <div className="editor">
                  <p>
                    正在编辑 {selected.software.name} {selected.version} / {selected.platform}
                  </p>
                  <label>
                    Markdown
                    <textarea value={markdown} onChange={(event) => setMarkdown(event.target.value)} />
                  </label>
                  <label>
                    脚本
                    <textarea value={script} onChange={(event) => setScript(event.target.value)} />
                  </label>
                  <div className="tabs">
                    <Button
                      type="button"
                      onClick={() => {
                        void savePlan(selected.id, markdown, script)
                          .then((saved) => {
                            setNote('已保存')
                            setSelected(saved)
                            return load('plans')
                          })
                          .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '保存失败'))
                      }}
                    >
                      保存
                    </Button>
                    <Button
                      type="button"
                      variant="sticker"
                      onClick={() => {
                        void regeneratePlan(selected.id)
                          .then((saved) => {
                            openPlan(saved)
                            setNote('已按 AI 重新生成')
                            return load('plans')
                          })
                          .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '重新生成失败'))
                      }}
                    >
                      让 AI 重新生成
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      onClick={() => {
                        void deletePlan(selected.id)
                          .then(() => {
                            setSelected(null)
                            setNote('已删除')
                            return load('plans')
                          })
                          .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '删除失败'))
                      }}
                    >
                      删除
                    </Button>
                  </div>
                </div>
              ) : null}
            </section>
          ) : null}
          {tab === 'feedback' ? (
            <section className="panel">
              <table>
                <thead>
                  <tr>
                    <th>软件</th>
                    <th>结论</th>
                    <th>内容</th>
                    <th>状态</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {feedback.map((item) => (
                    <tr key={item.id}>
                      <td>
                        {item.softwareName} {item.version} / {item.platform}
                      </td>
                      <td>{item.verdict === 'valid' ? '有效' : '无效'}</td>
                      <td>{item.content || '（没有文字）'}</td>
                      <td>{item.status === 'resolved' ? '已处理' : '未处理'}</td>
                      <td>
                        {item.status === 'pending' ? (
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => {
                              void updateFeedback(item.id, 'resolved')
                                .then(() => load('feedback'))
                                .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '更新失败'))
                            }}
                          >
                            标记已处理
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : null}
          {tab === 'stats' ? (
            <section className="panel">
              <table>
                <thead>
                  <tr>
                    <th>软件</th>
                    <th>版本</th>
                    <th>平台</th>
                    <th>次数</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.map((item) => (
                    <tr key={`${item.software?.name}-${item.version}-${item.platform}`}>
                      <td>{item.software?.name}</td>
                      <td>{item.version}</td>
                      <td>{item.platform}</td>
                      <td>{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : null}
        </>
      )}
    </main>
  )
}
