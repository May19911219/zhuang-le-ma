import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'

type PlanMarkdownProps = {
  markdown: string
}

/** 从 React 节点里抽出纯文本，供复制代码块使用。 */
function nodeText(node: unknown): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(nodeText).join('')
  if (node && typeof node === 'object' && 'props' in node) {
    const props = (node as { props?: { children?: unknown } }).props
    return nodeText(props?.children)
  }
  return ''
}

/** 渲染安装方案，代码块带复制按钮。 */
export function PlanMarkdown({ markdown }: PlanMarkdownProps) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          pre({ children }) {
            const text = nodeText(children).replace(/\n$/, '')
            return (
              <div className="code-shell">
                <button
                  type="button"
                  className="copy-code"
                  onClick={() => {
                    void navigator.clipboard.writeText(text)
                  }}
                >
                  复制
                </button>
                <pre>{children}</pre>
              </div>
            )
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  )
}

/** 复制整段脚本并短暂显示结果。 */
export function CopyScriptButton({ script }: { script: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <Button
      type="button"
      variant="quiet"
      onClick={() => {
        void navigator.clipboard.writeText(script).then(() => {
          setCopied(true)
          window.setTimeout(() => setCopied(false), 1200)
        })
      }}
    >
      {copied ? '已复制' : '复制脚本'}
    </Button>
  )
}
