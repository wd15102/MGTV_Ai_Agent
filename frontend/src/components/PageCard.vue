<template>
  <div class="page-card">
    <div v-if="title" class="page-card-header">
      <div class="page-card-title-row">
        <svg v-if="icon" class="page-card-icon" v-html="icon" viewBox="0 0 24 24" />
        <h3 class="page-card-title">{{ title }}</h3>
      </div>
      <div v-if="$slots.actions" class="page-card-actions">
        <slot name="actions" />
      </div>
    </div>
    <div class="page-card-body" :class="{ 'no-pad': noPad }">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  icon: { type: String, default: '' },
  noPad: { type: Boolean, default: false }
})
</script>

<style scoped>
.page-card {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e8e8e8;
  overflow: hidden;
  transition: all 0.2s ease;
}
.page-card:hover {
  border-color: #d6e4ff;
  box-shadow: 0 4px 16px rgba(22,119,255,0.06);
}
.page-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid #f0f0f0;
  background: linear-gradient(135deg, #fafbfc 0%, #fff 100%);
}
.page-card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-card-icon {
  width: 16px;
  height: 16px;
  color: #1677ff;
  flex-shrink: 0;
}
.page-card-title {
  font-size: 14px;
  font-weight: 700;
  color: #1f1f1f;
  margin: 0;
  letter-spacing: 0.03em;
}
.page-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-card-body {
  padding: 16px 18px;
}
.page-card-body.no-pad {
  padding: 0;
}
</style>
