<template>
  <PageCard title="用例管理" class="page-card-wrap">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-lg font-semibold text-[#1f1f1f]">用例管理</h2>
        <p class="text-xs text-[#999] mt-0.5">TEST CASE MANAGEMENT</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary text-xs px-3 py-1.5">
        <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        创建用例
      </button>
    </div>

    <!-- 筛选栏 -->
    <div class="card p-4">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <input v-model="searchQuery" placeholder="搜索用例名称..." class="input-field text-sm" />
        <select v-model="typeFilter" class="select-field text-sm">
          <option value="">全部类型</option>
          <option value="python">Python</option>
          <option value="yaml">YAML</option>
          <option value="natural">自然语言</option>
        </select>
        <button @click="loadCases" class="btn-secondary text-xs">搜索</button>
      </div>
    </div>

    <!-- 用例列表 -->
    <div class="card p-0 overflow-hidden">
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
            <tr v-for="item in cases" :key="item.id">
              <td class="font-mono text-[#999] text-xs">{{ item.id }}</td>
              <td class="font-medium text-[#1f1f1f]">{{ item.name }}</td>
              <td>
                <span :class="'badge ' + typeBadgeClass(item.type)" class="text-[10px]">{{ typeLabel(item.type) }}</span>
              </td>
              <td class="text-[#666] max-w-xs truncate text-xs">{{ item.description }}</td>
              <td class="font-mono text-xs text-[#999]">{{ formatTime(item.created_at) }}</td>
              <td>
                <div class="flex gap-1.5">
                  <button @click="viewCase(item)" class="btn-text text-xs px-2 py-1">查看</button>
                  <button @click="editCase(item)" class="btn-text text-xs px-2 py-1" style="color:#52c41a">编辑</button>
                  <button @click="deleteCase(item.id)" class="btn-text text-xs px-2 py-1" style="color:#ff4d4f">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="px-4 py-3 border-t border-gray-50 flex justify-between items-center">
        <p class="text-xs text-[#999]">共 {{ pagination.total }} 条</p>
        <div class="flex items-center gap-2">
          <button @click="changePage(pagination.page - 1)" :disabled="pagination.page <= 1"
                  class="btn-secondary text-xs px-2.5 py-1">上一页</button>
          <span class="text-xs text-[#666] px-2">{{ pagination.page }} / {{ totalPages }}</span>
          <button @click="changePage(pagination.page + 1)" :disabled="pagination.page >= totalPages"
                  class="btn-secondary text-xs px-2.5 py-1">下一页</button>
        </div>
      </div>
    </div>

    <!-- 创建/编辑模态框 -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal-content">
          <div class="modal-header">
            <h3 class="text-base font-semibold text-[#1f1f1f]">{{ editingCase ? '编辑用例' : '创建用例' }}</h3>
            <button @click="closeModal" class="p-1 rounded hover:bg-gray-50 text-[#999] hover:text-[#1f1f1f] transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          <div class="modal-body space-y-4">
            <div>
              <label class="block text-xs font-medium text-[#666] mb-1">名称</label>
              <input v-model="caseForm.name" class="input-field" placeholder="用例名称" />
            </div>
            <div>
              <label class="block text-xs font-medium text-[#666] mb-1">描述</label>
              <textarea v-model="caseForm.description" class="textarea-field" rows="2" placeholder="用例描述"></textarea>
            </div>
            <div>
              <label class="block text-xs font-medium text-[#666] mb-1">类型</label>
              <select v-model="caseForm.type" class="select-field">
                <option value="python">Python（复杂逻辑）</option>
                <option value="yaml">YAML（步骤化）</option>
                <option value="natural">自然语言（AI 辅助）</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-[#666] mb-1">内容</label>
              <p class="text-[10px] text-[#999] mb-1 font-mono">
                {{ caseForm.type === 'python' ? '// Python 代码' : caseForm.type === 'yaml' ? '# YAML 步骤定义' : '# 自然语言指令，AI 将自动生成脚本' }}
              </p>
              <textarea v-model="caseForm.content" class="textarea-field font-mono text-xs" rows="10" placeholder="在此输入..." spellcheck="false"></textarea>
            </div>
            <div v-if="caseForm.type === 'natural'" class="p-3 rounded-lg bg-[#f0f5ff] border border-[#d6e4ff]">
              <p class="text-xs text-[#1677ff] mb-1">💡 提示：自然语言模式使用示例：</p>
              <pre class="text-[10px] text-[#666] font-mono">{{ naturalExample }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="closeModal" class="btn-secondary text-xs">取消</button>
            <button @click="saveCase" class="btn-primary text-xs">保存</button>
          </div>
        </div>
      </div>
    </Teleport>
  </PageCard>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import PageCard from "@/components/PageCard.vue"
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()

const cases = ref([])
const searchQuery = ref('')
const typeFilter = ref('')
const showCreateModal = ref(false)
const editingCase = ref(null)
const caseForm = ref({ name: '', description: '', type: 'python', content: '' })
const pagination = ref({ page: 1, page_size: 20, total: 0 })
const totalPages = computed(() => Math.ceil(pagination.value.total / pagination.value.page_size))
const naturalExample = `打开设置应用\n点击"显示"选项\n检查是否显示"亮度"滑块\n返回首页`

async function loadCases() {
  try {
    const params = { page: pagination.value.page, page_size: pagination.value.page_size }
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
      await axios.put(`/api/v1/cases/${editingCase.value.id}`, caseForm.value)
      toast.success('用例更新成功')
    } else {
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

function editCase(caseItem) { viewCase(caseItem) }

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

function typeLabel(type) { return { python: 'Python', yaml: 'YAML', natural: '自然语言' }[type] || type }
function typeBadgeClass(type) { return { python: 'badge-info', yaml: 'badge-success', natural: 'badge-warning' }[type] || 'badge-info' }
function formatTime(isoString) {
  if (!isoString) return '-'
  return new Date(isoString).toLocaleString('zh-CN')
}

onMounted(() => loadCases())
</script>
