import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import GalleryPage from '../pages/GalleryPage.vue'
import EmptyPage from '../pages/EmptyPage.vue'
import DateViewPage from '../pages/DateViewPage.vue'
import SettingsPage from '../pages/SettingsPage.vue'

const API_BASE = 'http://127.0.0.1:8000'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage
  },
  {
    path: '/tags',
    name: 'tags',
    component: EmptyPage
  },
  {
    path: '/gallery',
    name: 'gallery',
    component: GalleryPage
  },
  {
    path: '/calendar',
    name: 'calendar',
    component: DateViewPage
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// After every route change, silently refresh the media library in the background.
// This keeps the DB in sync with the filesystem (prunes deleted files + orphaned cache)
// without blocking navigation.
let _refreshTimer = null
router.afterEach((to) => {
  // Skip automatic refresh when navigating to Settings page.
  // This prevents user actions in Settings (like clearing caches) from
  // immediately triggering a background refresh that may recreate files.
  if (to && (to.name === 'settings' || (to.path && to.path.startsWith('/settings')))) {
    if (_refreshTimer) {
      clearTimeout(_refreshTimer)
      _refreshTimer = null
    }
    return
  }

  if (_refreshTimer) clearTimeout(_refreshTimer)

  // Import may continue in a kept-alive page; avoid concurrent refresh jobs.
  if (window.__ptvImporting) return

  _refreshTimer = setTimeout(() => {
    if (window.__ptvImporting) return
    fetch(`${API_BASE}/api/admin/refresh`, { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        window.dispatchEvent(new CustomEvent('library-refreshed', { detail: data }))
      })
      .catch(() => {})
  }, 300)  // short debounce so rapid navigation doesn't spam the API
})

export default router
