import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import GalleryPage from '../pages/GalleryPage.vue'
import EmptyPage from '../pages/EmptyPage.vue'
import CalendarOverview from '../pages/CalendarOverview.vue'
import BrowsePage from '../pages/BrowsePage.vue'
import CategorySettingsPage from '../pages/CategorySettingsPage.vue'
import SettingsPage from '../pages/SettingsPage.vue'
import TrashPage from '../pages/TrashPage.vue'

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
    component: CalendarOverview
  },
  {
    path: '/calendar/:group',
    name: 'browse-group',
    component: BrowsePage,
    props: true,
    meta: { reuseKey: 'browse' }
  },
  {
    path: '/calendar/:group/:albumPath+',
    name: 'browse-album',
    component: BrowsePage,
    props: true,
    meta: { reuseKey: 'browse' }
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsPage
  },
  {
    path: '/settings/categories',
    name: 'settings-categories',
    component: CategorySettingsPage
  },
  {
    path: '/trash',
    name: 'trash',
    component: TrashPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
