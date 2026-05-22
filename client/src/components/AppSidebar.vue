<template>
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">

    <div class="sidebar-header">
      <div class="sidebar-logo" v-show="!isCollapsed">
        <span class="sidebar-logo-name">{{ appName }}</span>
        <span class="sidebar-logo-sub">{{ appSubtitle }}</span>
      </div>
      <div class="sidebar-logo-icon" v-show="isCollapsed">C</div>
      <button class="sidebar-toggle" @click="toggleCollapse" :title="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'">
        <svg class="toggle-icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
      </button>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="sidebar-nav-item"
        :class="{ active: isActive(item) }"
        :data-label="item.label"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round">
          <path :d="item.icon" />
        </svg>
        <span v-show="!isCollapsed">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <LanguageSwitcher v-show="!isCollapsed" />
      <ProfileMenu
        @show-profile-details="$emit('show-profile-details')"
        @show-tasks="$emit('show-tasks')"
      />
    </div>

  </aside>
</template>

<script>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '../composables/useI18n'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ProfileMenu from './ProfileMenu.vue'

const ICON_OVERVIEW    = 'M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z'
const ICON_INVENTORY   = 'M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9'
const ICON_ORDERS      = 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01'
const ICON_RESTOCKING  = 'M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99'
const ICON_FINANCE     = 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z'
const ICON_DEMAND      = 'M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941'
const ICON_REPORTS     = 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25M9 16.5v.75m3-3v3M15 12v5.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z'

export default {
  name: 'AppSidebar',
  components: { LanguageSwitcher, ProfileMenu },
  emits: ['show-profile-details', 'show-tasks', 'update:collapsed'],
  setup(props, { emit }) {
    const route = useRoute()
    const { t } = useI18n()

    const appName = 'Catalyst'
    const appSubtitle = 'Components'

    const navItems = [
      { path: '/',          label: t('nav.overview'),       icon: ICON_OVERVIEW  },
      { path: '/inventory', label: t('nav.inventory'),      icon: ICON_INVENTORY },
      { path: '/orders',      label: t('nav.orders'),         icon: ICON_ORDERS      },
      { path: '/restocking', label: t('nav.restocking'),    icon: ICON_RESTOCKING  },
      { path: '/spending',   label: t('nav.finance'),       icon: ICON_FINANCE     },
      { path: '/demand',    label: t('nav.demandForecast'), icon: ICON_DEMAND    },
      { path: '/reports',   label: 'Reports',               icon: ICON_REPORTS   },
    ]

    const isCollapsed = ref(false)

    const isActive = (item) => {
      if (item.path === '/') return route.path === '/'
      return route.path.startsWith(item.path)
    }

    const toggleCollapse = () => {
      isCollapsed.value = !isCollapsed.value
    }

    const checkBreakpoint = () => {
      isCollapsed.value = window.innerWidth < 1024
    }

    // Propagate collapse state to App.vue whenever it changes
    watch(isCollapsed, (val) => emit('update:collapsed', val))

    onMounted(() => {
      checkBreakpoint()
      // Emit initial state so App.vue margin is correct from the start
      emit('update:collapsed', isCollapsed.value)
      window.addEventListener('resize', checkBreakpoint)
    })

    onUnmounted(() => {
      window.removeEventListener('resize', checkBreakpoint)
    })

    return { appName, appSubtitle, navItems, isCollapsed, isActive, toggleCollapse }
  }
}
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 240px;
  background: #0f172a;
  border-right: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  z-index: 100;
  overflow: hidden;
  transition: width 0.25s ease;
}

.sidebar.collapsed {
  width: 64px;
}

/* ── Header ── */
.sidebar-header {
  padding: 1.25rem 1rem 1.25rem 1.25rem;
  border-bottom: 1px solid #1e293b;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 64px;
  gap: 0.5rem;
}

.sidebar.collapsed .sidebar-header {
  justify-content: center;
  padding: 1.25rem 0;
  flex-direction: column;
  gap: 0.5rem;
}

.sidebar-logo {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  flex: 1;
  min-width: 0;
}

.sidebar-logo-name {
  font-size: 1rem;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: -0.025em;
  white-space: nowrap;
}

.sidebar-logo-sub {
  font-size: 0.75rem;
  color: #475569;
  font-weight: 400;
  white-space: nowrap;
}

/* Small branded square shown when collapsed */
.sidebar-logo-icon {
  width: 32px;
  height: 32px;
  background: #3b82f6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

/* ── Toggle button ── */
.sidebar-toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.375rem;
  border-radius: 6px;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s ease, color 0.15s ease;
}

.sidebar-toggle:hover {
  background: #1e293b;
  color: #94a3b8;
}

.toggle-icon {
  width: 16px;
  height: 16px;
  transition: transform 0.25s ease;
}

/* Rotate chevron to point right when collapsed */
.sidebar.collapsed .toggle-icon {
  transform: rotate(180deg);
}

/* ── Nav ── */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0.75rem 0;
}

.sidebar-nav::-webkit-scrollbar { width: 4px; }
.sidebar-nav::-webkit-scrollbar-track { background: transparent; }
.sidebar-nav::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }

.sidebar-nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  margin: 0.125rem calc(0.5rem - 3px);
  border-radius: 6px;
  color: #94a3b8;
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.15s ease, color 0.15s ease;
  border-left: 3px solid transparent;
  position: relative;
  white-space: nowrap;
}

.sidebar-nav-item:hover {
  background: #1e293b;
  color: #e2e8f0;
}

.sidebar-nav-item.active {
  background: #1e293b;
  color: #f8fafc;
  border-left-color: #3b82f6;
}

/* Collapsed nav item: center the icon */
.sidebar.collapsed .sidebar-nav-item {
  justify-content: center;
  padding: 0.75rem 0;
  margin: 0.125rem 0.5rem;
  border-left-width: 0;
  border-radius: 8px;
}

.sidebar.collapsed .sidebar-nav-item.active {
  background: #1e3a6e;
}

/* CSS tooltip shown on hover in collapsed mode */
.sidebar.collapsed .sidebar-nav-item::after {
  content: attr(data-label);
  position: absolute;
  left: calc(100% + 10px);
  top: 50%;
  transform: translateY(-50%);
  background: #1e293b;
  color: #e2e8f0;
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s ease;
  z-index: 200;
  border: 1px solid #334155;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.sidebar.collapsed .sidebar-nav-item:hover::after {
  opacity: 1;
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* ── Footer ── */
.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #1e293b;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.sidebar.collapsed .sidebar-footer {
  justify-content: center;
  padding: 0.875rem 0;
}
</style>
