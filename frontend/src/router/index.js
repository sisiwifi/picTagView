import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import GalleryPage from '../pages/GalleryPage.vue'
import EmptyPage from '../pages/EmptyPage.vue'
import CalendarOverview from '../pages/CalendarOverview.vue'
import BrowsePage from '../pages/BrowsePage.vue'
import CategorySettingsPage from '../pages/CategorySettingsPage.vue'
import SettingsPage from '../pages/SettingsPage.vue'
import SearchPage from '../pages/SearchPage.vue'
import FavoritesPage from '../pages/FavoritesPage.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage
  },
  {
    path: '/search',
    name: 'search',
    component: SearchPage
  },
  {
    path: '/tags',
    name: 'tags',
    component: EmptyPage
  },
  {
    path: '/gallery',
    name: 'gallery',
    component: GalleryPage,
    meta: { keepAlive: true }
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
    path: '/favorites',
    name: 'favorites',
    component: FavoritesPage
  },
  {
    path: '/favorites/:collectionId',
    name: 'browse-collection',
    component: BrowsePage,
    props: true,
    meta: { reuseKey: 'browse', browseContract: 'collection' }
  },
  {
    path: '/settings/categories',
    name: 'settings-categories',
    component: CategorySettingsPage
  },
  {
    path: '/trash',
    name: 'trash',
    component: BrowsePage,
    meta: { reuseKey: 'browse', browseContract: 'trash' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
