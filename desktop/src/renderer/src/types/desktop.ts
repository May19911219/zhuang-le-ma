export type InstallLog = {
  id: string
  stream: 'stdout' | 'stderr' | 'exit'
  chunk: string
}

export type DesktopApi = {
  getPlatform: () => Promise<string>
  runInstall: (payload: { script: string; shell: 'powershell' | 'bash'; elevate: boolean }) => Promise<{ id: string }>
  onInstallLog: (callback: (entry: InstallLog) => void) => () => void
  openExternal: (url: string) => Promise<void>
}

declare global {
  interface Window {
    desktop?: DesktopApi
  }
}

export {}
