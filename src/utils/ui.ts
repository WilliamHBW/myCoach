// Toast 提示
export const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
  const toast = document.createElement('div')
  toast.className = `custom-toast toast-${type}`
  toast.textContent = message
  document.body.appendChild(toast)
  setTimeout(() => toast.classList.add('show'), 10)
  setTimeout(() => {
    toast.classList.remove('show')
    setTimeout(() => document.body.removeChild(toast), 300)
  }, 2000)
}

// Loading 提示
let loadingEl: HTMLDivElement | null = null

export const showLoading = (message: string) => {
  loadingEl = document.createElement('div')
  loadingEl.className = 'custom-loading'
  loadingEl.innerHTML = `<div class="loading-spinner"></div><span>${message}</span>`
  document.body.appendChild(loadingEl)
  setTimeout(() => loadingEl?.classList.add('show'), 10)
}

export const hideLoading = () => {
  if (loadingEl) {
    loadingEl.classList.remove('show')
    setTimeout(() => {
      loadingEl?.remove()
      loadingEl = null
    }, 300)
  }
}

// 确认弹窗
interface ConfirmOptions {
  title: string
  content: string
  confirmText?: string
  cancelText?: string
  onConfirm?: () => void
  onCancel?: () => void
}

export const showConfirm = (options: ConfirmOptions) => {
  const { title, content, confirmText = '确定', cancelText = '取消', onConfirm, onCancel } = options
  
  const overlay = document.createElement('div')
  overlay.className = 'custom-modal-overlay'
  
  overlay.innerHTML = `
    <div class="custom-modal">
      <div class="modal-title">${title}</div>
      <div class="modal-content">${content}</div>
      <div class="modal-actions">
        <button class="modal-btn cancel">${cancelText}</button>
        <button class="modal-btn confirm">${confirmText}</button>
      </div>
    </div>
  `
  
  document.body.appendChild(overlay)
  setTimeout(() => overlay.classList.add('show'), 10)
  
  const close = () => {
    overlay.classList.remove('show')
    setTimeout(() => overlay.remove(), 300)
  }
  
  overlay.querySelector('.cancel')?.addEventListener('click', () => {
    close()
    onCancel?.()
  })
  
  overlay.querySelector('.confirm')?.addEventListener('click', () => {
    close()
    onConfirm?.()
  })
}

// 简单弹窗（只有确定按钮）
export const showAlert = (title: string, content: string) => {
  return new Promise<void>((resolve) => {
    showConfirm({
      title,
      content,
      cancelText: '',
      onConfirm: resolve
    })
  })
}

