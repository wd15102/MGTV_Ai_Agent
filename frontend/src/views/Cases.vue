<template>
  <div class="space-y-6">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <h2 class="text-3xl font-bold text-gray-900">📝 用例管理</h2>
      <button @click="showCreateModal = true" class="btn-primary">
        ➕ 创建用例
      </button>
    </div>

    <!-- 筛选栏 -->
    <div class="card">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <input 
          v-model="searchQuery" 
          placeholder="搜索用例名称..." 
          class="input-field"
        />
        <select v-model="typeFilter" class="select-field">
          <option value="">全部类型</option>
          <option value="python">Python</option>
          <option value="yaml">YAML</option>
          <option value="natural">自然语言</option>
        </select>
        <button @click="loadCases" class="btn-secondary">
          🔍 搜索
        </button>
      </div>
    </div>

    <!-- 用例列表 -->
    <div class="card">
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>类型</th>
              <th>描述</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="case in cases" :key="case.id">
              <td>{{ case.id }}</td>
              <td class="font-medium text-gray-900">{{ case.name }}</td>
              <td>
                <span :class="typeBadgeClass(case.type)" class="badge">
                  {{ typeLabel(case.type) }}
                </span>
              </td>
              <td class="text-gray-500 max-w-xs truncate">{{ case.description }}</td>
              <td class="text-sm text-gray-500">{{ formatTime(case.created_at) }}</td>
              <td>
                <div class="flex space-x-2">
                  <button @click="viewCase(case)" class="text-blue-600 hover:text-blue-800">
                    查看
                  </button>
                  <button @click="editCase(case)" class="text-green-600 hover:text-green-800">
                    编辑
                  </button>
                  <button @click="deleteCase(case.id)" class="text-red-600 hover:text-red-800">
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="mt-4 flex justify-between items-center">
        <p class="text-sm text-gray-500">
          共 {{ pagination.total }} 条记录
        </p>
        <div class="flex space-x-2">
          <button 
            @click="changePage(pagination.page - 1)" 
            :disabled="pagination.page <= 1"
            class="btn-secondary text-sm"
          >
            上一页
          </button>
          <span class="px-3 py-2 text-sm text-gray-700">
            {{ pagination.page }} / {{ totalPages }}
          </span>
          <button 
            @click="changePage(pagination.page + 1)"
            :disabled="pagination.page >= totalPages"
            class="btn-secondary text-sm"
          >
            下一页
          </button>
        </div>
      </div>
    </div>

    <!-- 创建/编辑模态框 -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl p-6 w-full max-w-2xl max-h-screen overflow-y-auto">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-xl font-bold">{{ editingCase ? '编辑用例' : '创建用例' }}</h3>
          <button @click="closeModal" class="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <input v-model="caseForm.name" class="input-field" placeholder="用例名称" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea v-model="caseForm.description" class="input-field" rows="2" placeholder="用例描述"></textarea>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">类型</label>
            <select v-model="caseForm.type" class="select-field">
              <option value="python">Python（复杂逻辑）</option>
              <option value="yaml">YAML（步骤化）</option>
              <option value="natural">自然语言（AI 辅助）</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">内容</label>
            <div class="text-xs text-gray-500 mb-2">
              <span v-if="caseForm.type === 'python'">请输入 Python 代码</span>
              <span v-else-if="caseForm.type === 'yaml'">请输入 YAML 步骤定义</span>
              <span v-else>请输入自然语言指令，AI 将自动生成脚本</span>
            </div>
            <textarea 
              v-model="caseForm.content" 
              class="input-field font-mono text-sm" 
              rows="12"
              placeholder="在此输入..."
            ></textarea>
          </div>

          <div v-if="caseForm.type === 'natural'" class="bg-blue-50 p-3 rounded-lg">
            <p class="text-sm text-blue-800">
              💡 提示：自然语言模式使用示例：
            </p>
            <pre class="text-xs text-blue-600 mt-1">{{ naturalExample }}</pre>
          </div>
        </div>

        <div class="mt-6 flex justify-end space-x-2">
          <button @click="closeModal" class="btn-secondary">取消</button>
          <button @click="saveCase" class="btn-primary">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()

const cases = ref([])
const searchQuery = ref('')
const typeFilter = ref('')
const showCreateModal = ref(false)
const editingCase = ref(null)
const caseForm = ref({
  name: '',
  description: '',
  type: 'python',
  content: ''
})
const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0
})

const totalPages = computed(() => Math.ceil(pagination.value.total / pagination.value.page_size))

const naturalExample = `打开设置应用
点击"显示"选项
检查是否显示"亮度"滑块
返回首页`

async function loadCases() {
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.page_size
    }
    if (typeFilter.value) params.type = typeFilter.value
    
    const res = await axios.get('/api/v1/cases', { params })
    cases.value = res.data.data
    pagination.value.total = res.data.pagination.total
  } catch (error) {
    toast.error('加载用例失败: ' + error.message)
  }
}

async function saveCase() {
  try {
    if (editingCase.value) {
      // 更新
      await axios.put(`/api/v1/cases/${editingCase.value.id}`, caseForm.value)
      toast.success('用例更新成功')
    } else {
      // 创建
      await axios.post('/api/v1/cases', caseForm.value)
      toast.success('用例创建成功')
    }
    closeModal()
    await loadCases()
  } catch (error) {
    toast.error('保存失败: ' + error.message)
  }
}

function viewCase(caseItem) {
  editingCase.value = { ...caseItem }
  caseForm.value = { ...caseItem }
  showCreateModal.value = true
}

function editCase(caseItem) {
  viewCase(caseItem)
}

async function deleteCase(caseId) {
  if (!confirm('确定要删除此用例吗？')) return
  
  try {
    await axios.delete(`/api/v1/cases/${caseId}`)
    toast.success('用例删除成功')
    await loadCases()
  } catch (error) {
    toast.error('删除失败: ' + error.message)
  }
}

function closeModal() {
  showCreateModal.value = false
  editingCase.value = null
  caseForm.value = { name: '', description: '', type: 'python', content: '' }
}

function changePage(page) {
  if (page < 1 || page > totalPages.value) return
  pagination.value.page = page
  loadCases()
}

function typeLabel(type) {
  const labels = { python: 'Python', yaml: 'YAML', natural: '自然语言' }
  return labels[type] || type
}

function typeBadgeClass(type) {
  return {
    'bg-blue-100 text-blue-800': type === 'python',
    'bg-green-100 text-green-800': type === 'yaml',
    'bg-purple-100 text-purple-800': type === 'natural'
  }
}

function formatTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadCases()
})
</script>
