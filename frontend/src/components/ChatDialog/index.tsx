import React, { useState, useRef, useEffect } from 'react'
import { usePlanStore } from '../../store/usePlanStore'
import { planApi } from '../../services/api'
import { showToast } from '../../utils/ui'
import './index.scss'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatDialogProps {
  isOpen: boolean
  onClose: () => void
  initialMessage?: string
}

export const ChatDialog: React.FC<ChatDialogProps> = ({ isOpen, onClose, initialMessage }) => {
  const { currentPlan, updatePlanWeeks } = usePlanStore()
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [pendingUpdate, setPendingUpdate] = useState<any[] | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 首次打开且没有消息时添加欢迎消息
  useEffect(() => {
    if (isOpen && chatMessages.length === 0) {
      setChatMessages([{
        role: 'assistant',
        content: '👋 你好！我是你的 AI 教练。你可以告诉我想如何调整训练计划，或者询问运动相关的问题，比如：\n\n• "我这周膝盖有点不舒服，能减少腿部训练吗？"\n• "能把周三的训练改到周四吗？"\n• "根据我的运动记录，现在的进度合适吗？"\n• "我想增加一些核心训练"\n\n请告诉我你的需求！'
      }])
    }
  }, [isOpen])

  // 自动滚动到最新消息
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chatMessages])

  // 打开对话框时聚焦输入框
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleClearChat = () => {
    setChatMessages([{
      role: 'assistant',
      content: '👋 对话已清理。有什么我可以帮你的吗？'
    }])
    setPendingUpdate(null)
    showToast('对话已清理', 'success')
  }

  const handleSyncPlan = async () => {
    if (!pendingUpdate) return
    
    try {
      await updatePlanWeeks(pendingUpdate)
      setPendingUpdate(null)
      showToast('训练计划同步成功', 'success')
    } catch (e: any) {
      showToast(e.message || '同步失败', 'error')
    }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !currentPlan) return

    const userMessage = inputMessage.trim()
    setInputMessage('')
    
    // 添加用户消息
    const newMessages: ChatMessage[] = [...chatMessages, { role: 'user', content: userMessage }]
    setChatMessages(newMessages)
    
    setIsLoading(true)

    try {
      const result = await planApi.chat(currentPlan.id, userMessage, chatMessages)
      
      // 添加 AI 回复
      setChatMessages(prev => [...prev, { role: 'assistant', content: result.message }])
      
      // 如果有计划更新，存入待同步状态
      if (result.updatedPlan) {
        setPendingUpdate(result.updatedPlan)
        showToast('AI 已建议修改计划，请点击“同步计划”查看', 'success')
      }
      
    } catch (error: any) {
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `❌ 抱歉，处理请求时出错了：${error.message || '请重试'}` 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  if (!isOpen) return null

  return (
    <div className='chat-dialog-overlay' onClick={onClose}>
      <div className='chat-dialog' onClick={e => e.stopPropagation()}>
        <div className='chat-header'>
          <div className='chat-title'>
            <span className='chat-icon'>🏋️</span>
            <span>AI 教练 · 助手</span>
          </div>
          <button className='chat-close' onClick={onClose}>
            ✕
          </button>
        </div>

        <div className='chat-toolbar'>
          <button className='toolbar-btn clear' onClick={handleClearChat}>
            🗑️ 清理对话
          </button>
          <button 
            className={`toolbar-btn sync ${pendingUpdate ? 'active' : ''}`} 
            onClick={handleSyncPlan}
            disabled={!pendingUpdate}
          >
            🔄 同步计划
          </button>
        </div>
        
        <div className='chat-messages'>
          {chatMessages.map((msg, index) => (
            <div key={index} className={`chat-message ${msg.role}`}>
              <div className='message-content'>
                {msg.content.split('\n').map((line, i) => (
                  <React.Fragment key={i}>
                    {line}
                    {i < msg.content.split('\n').length - 1 && <br />}
                  </React.Fragment>
                ))}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className='chat-message assistant'>
              <div className='message-content loading'>
                <span className='typing-dot'></span>
                <span className='typing-dot'></span>
                <span className='typing-dot'></span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
        
        <div className='chat-input-area'>
          <textarea
            ref={inputRef}
            className='chat-input'
            placeholder='向 AI 教练提问或调整计划...'
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
            rows={1}
          />
          <button 
            className='chat-send'
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}

