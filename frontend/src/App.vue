<template>
  <RouterView />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<style>
:root {
  --bg-primary:   #1e1e1e;
  --bg-secondary: #252525;
  --bg-tertiary:  #2d2d2d;
  --bg-elevated:  #333333;

  --border-subtle:  #333333;
  --border-default: #3d3d3d;
  --border-strong:  #505050;

  --text-primary: #dcddde;
  --text-muted:   #888888;
  --text-faint:   #555555;

  --accent:       #7f6df2;
  --accent-hover: #8b8cf8;

  --color-red:    #e05252;
  --color-green:  #4caf50;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica,
    Arial, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  color: var(--text-primary);
  background: var(--bg-primary);
}

#app {
  min-height: 100vh;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #3d3d3d;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #505050;
}
</style>
