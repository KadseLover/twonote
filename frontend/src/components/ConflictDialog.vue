<template>
  <transition name="dialog-fade">
    <div v-if="visible" class="overlay" @click.self="choose('cancel')">
      <div class="dialog" role="dialog" aria-modal="true">
        <h3 class="title">{{ title }}</h3>
        <p class="message">
          <template v-if="message">{{ message }}</template>
          <template v-else>
            „<strong>{{ filename }}</strong>" ist bereits vorhanden. Was möchtest du tun?
          </template>
        </p>

        <div class="actions">
          <button class="btn primary" @click="choose('version')">
            Eigene Version hochladen
          </button>
          <button class="btn danger" @click="choose('overwrite')">
            Überschreiben
          </button>
          <button class="btn ghost" @click="choose('cancel')">
            Abbrechen
          </button>
        </div>

        <p class="hint">
          „Eigene Version" behält die alte Fassung – sie bleibt unter „Versionen"
          abrufbar. „Überschreiben" ersetzt sie endgültig.
        </p>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
export type ConflictChoice = 'version' | 'overwrite' | 'cancel'

withDefaults(
  defineProps<{
    visible: boolean
    filename?: string
    title?: string
    message?: string
  }>(),
  {
    filename: '',
    title: 'Datei existiert bereits',
    message: '',
  },
)

const emit = defineEmits<{
  (e: 'choose', choice: ConflictChoice): void
}>()

function choose(choice: ConflictChoice) {
  emit('choose', choice)
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
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
  margin: 0 0 1.25rem;
  font-size: 0.875rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.message strong {
  color: var(--text-primary);
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn {
  width: 100%;
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

.btn.danger:hover {
  background: #2d1515;
  color: var(--color-red);
  border-color: #4d2020;
}

.btn.ghost {
  background: transparent;
}

.hint {
  margin: 1rem 0 0;
  font-size: 0.75rem;
  color: var(--text-faint);
  line-height: 1.45;
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
