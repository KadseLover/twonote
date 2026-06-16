<template>
  <transition name="dialog-fade">
    <div v-if="visible" class="overlay" @click.self="cancel">
      <div class="dialog" role="dialog" aria-modal="true">
        <h3 class="title">{{ title }}</h3>
        <p v-if="message" class="message">{{ message }}</p>
        <input
          ref="inputEl"
          v-model="value"
          class="input"
          :placeholder="placeholder"
          @keydown.enter.prevent="submit"
          @keydown.esc.prevent="cancel"
        />
        <div class="actions">
          <button class="btn primary" @click="submit">{{ confirmText }}</button>
          <button class="btn ghost" @click="cancel">{{ cancelText }}</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = withDefaults(
  defineProps<{
    visible: boolean
    title?: string
    message?: string
    placeholder?: string
    defaultValue?: string
    confirmText?: string
    cancelText?: string
  }>(),
  {
    title: 'Name eingeben',
    message: '',
    placeholder: '',
    defaultValue: '',
    confirmText: 'OK',
    cancelText: 'Abbrechen',
  },
)

const emit = defineEmits<{
  (e: 'submit', value: string): void
  (e: 'cancel'): void
}>()

const value = ref(props.defaultValue)
const inputEl = ref<HTMLInputElement | null>(null)

watch(
  () => props.visible,
  async (v) => {
    if (!v) return
    value.value = props.defaultValue
    await nextTick()
    inputEl.value?.focus()
    inputEl.value?.select()
  },
)

function submit() {
  emit('submit', value.value)
}

function cancel() {
  emit('cancel')
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 110;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.55);
  padding: 1rem;
}

.dialog {
  width: 100%;
  max-width: 420px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
}

.title {
  margin: 0 0 0.5rem;
  font-size: 1.0625rem;
  color: var(--text-primary);
}

.message {
  margin: 0 0 0.9rem;
  font-size: 0.875rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.input {
  width: 100%;
  box-sizing: border-box;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 5px;
  color: var(--text-primary);
  font-size: 0.9375rem;
  padding: 0.55rem 0.7rem;
  margin-bottom: 1.25rem;
  outline: none;
  transition: border-color 0.15s;
}

.input:focus {
  border-color: var(--accent);
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn {
  flex: 1;
  padding: 0.6rem 0.9rem;
  border-radius: 5px;
  border: 1px solid var(--border-default);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s;
}

.btn:hover {
  background: var(--bg-elevated);
}

.btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.btn.primary:hover {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.btn.ghost {
  background: transparent;
}

.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.15s;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
