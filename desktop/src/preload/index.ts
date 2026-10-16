import { contextBridge, ipcRenderer } from 'electron'

export type InstallLog = {
  id: string
  stream: 'stdout' | 'stderr' | 'exit'
  chunk: string
}

const desktop = {
  getPlatform: (): Promise<string> => ipcRenderer.invoke('app:platform'),
  runInstall: (payload: { script: string; shell: 'powershell' | 'bash'; elevate: boolean }): Promise<{ id: string }> =>
    ipcRenderer.invoke('install:run', payload),
  onInstallLog: (callback: (entry: InstallLog) => void): (() => void) => {
    const listener = (_event: unknown, entry: InstallLog): void => callback(entry)
    ipcRenderer.on('install:log', listener)
    return () => ipcRenderer.removeListener('install:log', listener)
  },
  openExternal: (url: string): Promise<void> => ipcRenderer.invoke('shell:open', url),
}

contextBridge.exposeInMainWorld('desktop', desktop)
