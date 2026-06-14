import { ref, onMounted, onBeforeUnmount } from 'vue'

const QUERY = '(max-width: 760px)'

/**
 * Reaktiver Mobil-Breakpoint. Gibt ein `isMobile`-Ref zurück, das dem
 * Media-Query folgt (inkl. Listener-Auf-/Abbau).
 */
export function useIsMobile() {
  const mql = typeof window !== 'undefined' ? window.matchMedia(QUERY) : null
  const isMobile = ref(mql ? mql.matches : false)

  function update(e: MediaQueryListEvent) {
    isMobile.value = e.matches
  }

  onMounted(() => mql?.addEventListener('change', update))
  onBeforeUnmount(() => mql?.removeEventListener('change', update))

  return { isMobile }
}
