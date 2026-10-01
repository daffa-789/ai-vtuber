import { contextBridge } from 'electron'
contextBridge.exposeInMainWorld('silverWolfDesktop', { platform: process.platform, versions: process.versions })
