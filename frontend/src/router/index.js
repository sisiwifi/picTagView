import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import GalleryPage from '../pages/GalleryPage.vue'
import EmptyPage from '../pages/EmptyPage.vue'
import DateViewPage from '../pages/DateViewPage.vue'

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
    component: EmptyPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
