import { generateICS } from '../../utils/calendar'

export default function Plan() {
  const { currentPlan, clearPlan } = usePlanStore()
  const [activeWeek, setActiveWeek] = useState(0)

  // ... (keep existing methods)

  const handleExport = () => {
    if (!currentPlan) return

    Taro.showLoading({ title: '生成日历...' })
    try {
      // 1. Generate ICS content
      const icsData = generateICS(currentPlan)
      
      // 2. Save to temporary file
      const fs = Taro.getFileSystemManager()
      const filePath = `${Taro.env.USER_DATA_PATH}/training_plan.ics`
      
      fs.writeFile({
        filePath,
        data: icsData,
        encoding: 'utf8',
        success: () => {
          Taro.hideLoading()
          // 3. Open share menu / file viewer
          Taro.shareFileMessage({
            filePath,
            fileName: 'MyCoach_Training_Plan.ics',
            success: () => {
              console.log('Share success')
            },
            fail: (err) => {
              // Fallback for some environments: openDocument (might not open .ics on all androids)
              // Or simple showToast
              console.log('Share failed, try openDocument', err)
              Taro.openDocument({
                filePath,
                fileType: 'ics', // 'ics' might not be standard supported type in wx.openDocument
                showMenu: true,
                success: () => console.log('Open success'),
                fail: (e) => {
                   Taro.showModal({
                     title: '导出成功',
                     content: `文件已保存至: ${filePath}。由于系统限制，请手动在文件管理器中打开。`,
                     showCancel: false
                   })
                }
              })
            }
          })
        },
        fail: (err) => {
          Taro.hideLoading()
          Taro.showToast({ title: '保存文件失败', icon: 'none' })
          console.error(err)
        }
      })
    } catch (e) {
      Taro.hideLoading()
      console.error(e)
      Taro.showToast({ title: '导出出错', icon: 'none' })
    }
  }

  // ... (render logic)

        {/* Footer Actions */}
        <View className='footer-actions'>
          <Button className='export-btn' onClick={handleExport}>导出到日历</Button>
          <Button className='delete-btn' onClick={handleDelete}>删除当前计划</Button>
        </View>
