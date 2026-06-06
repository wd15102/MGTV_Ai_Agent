<template>
  <div id="app" class="min-h-screen bg-gray-100">
    <!-- 导航栏 -->
    <nav class="bg-white shadow-lg">
      <div class="max-w-full mx-auto px-4">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <h1 class="text-2xl font-bold text-blue-600">🤖 AI 智能测试大屏平台</h1>
          </div>
          <div class="flex items-center space-x-4">
            <router-link to="/" class="nav-link">📊 大屏</router-link>
            <router-link to="/cases" class="nav-link">📝 用例管理</router-link>
            <router-link to="/devices" class="nav-link">📱 设备监控</router-link>
            <router-link to="/executions" class="nav-link">▶️ 执行控制</router-link>
            <router-link to="/reports" class="nav-link">📄 报告</router-link>
            <router-link to="/ai" class="nav-link">🧠 AI 状态</router-link>
          </div>
        </div>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="max-w-full mx-auto px-4 py-6">
      <router-view />
    </main>
  </div>
</template>

<script setup>
// 主应用组件
</script>

<style>
.nav-link {
  @apply px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 transition-colors;
}

.nav-link.router-link-active {
  @apply text-blue-600 bg-blue-50;
}
</style>
