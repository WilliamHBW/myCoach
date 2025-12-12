import { View, Text, Input, Button, Picker, Textarea } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useSettingsStore, ModelProvider } from '../../store/useSettingsStore'
import './index.scss'

const PROVIDERS: { value: ModelProvider; label: string }[] = [
  { value: 'openai', label: 'OpenAI (GPT-4/3.5)' },
  { value: 'deepseek', label: 'DeepSeek (深度求索)' },
  { value: 'claude', label: 'Anthropic (Claude)' },
]

export default function Settings() {
  const { 
    apiKey, 
    modelProvider, 
    systemPrompt, 
    setApiKey, 
    setModelProvider, 
    setSystemPrompt 
  } = useSettingsStore()

  const handleSave = () => {
    // Zustand persist middleware already saves changes, 
    // but we can add a visual feedback here.
    Taro.showToast({
      title: '设置已保存',
      icon: 'success',
      duration: 2000
    })
  }

  const currentProviderIndex = PROVIDERS.findIndex(p => p.value === modelProvider)

  return (
    <View className='settings-page'>
      <View className='section'>
        <Text className='section-title'>模型选择</Text>
        <Picker 
          mode='selector' 
          range={PROVIDERS} 
          rangeKey='label'
          value={currentProviderIndex}
          onChange={(e) => setModelProvider(PROVIDERS[e.detail.value].value)}
        >
          <View className='picker-item'>
            <Text>当前选择：</Text>
            <Text className='picker-value'>{PROVIDERS[currentProviderIndex]?.label || '请选择'}</Text>
          </View>
        </Picker>
      </View>

      <View className='section'>
        <Text className='section-title'>API Key</Text>
        <Input
          className='input'
          type='text'
          password
          placeholder='请输入您的 API Key'
          value={apiKey}
          onInput={(e) => setApiKey(e.detail.value)}
        />
        <Text className='hint'>您的 Key 仅存储在本地设备，不会上传到我们的服务器。</Text>
      </View>

      <View className='section'>
        <Text className='section-title'>系统提示词 (System Prompt)</Text>
        <Textarea
          className='textarea'
          placeholder='设置 AI 教练的人设...'
          value={systemPrompt}
          onInput={(e) => setSystemPrompt(e.detail.value)}
          maxlength={500}
        />
      </View>

      <Button className='save-btn' onClick={handleSave}>保存配置</Button>
    </View>
  )
}
