import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'

const DashboardPage = () => import('@/pages/DashboardPage.vue')
const DetectPage = () => import('@/pages/DetectPage.vue')
const WelcomePage = () => import('@/pages/WelcomePage.vue')
const ResultPage = () => import('@/pages/ResultPage.vue')
const HistoryDetailPage = () => import('@/pages/HistoryDetailPage.vue')
const HistoryPage = () => import('@/pages/HistoryPage.vue')
const ChatPage = () => import('@/pages/ChatPage.vue')
const KnowledgePage = () => import('@/pages/KnowledgePage.vue')
const QuizPage = () => import('@/pages/QuizPage.vue')
const NotFoundPage = () => import('@/pages/NotFoundPage.vue')

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/welcome', name: 'welcome', component: WelcomePage, meta: { title: '欢迎页' } },
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', name: 'dashboard', component: DashboardPage, meta: { title: '首页', bodyClass: 'page-home page-home-v2', mainClass: 'site-main--home homev2-main' } },
        { path: 'detect/:kind(image|video|audio)', name: 'detect', component: DetectPage, meta: { title: '检测工作台', bodyClass: 'page-detect' } },
        { path: 'results/:taskId', name: 'result', component: ResultPage, meta: { title: '检测结果', bodyClass: 'page-result' } },
        { path: 'history', name: 'history', component: HistoryPage, meta: { title: '历史中心', bodyClass: 'page-history' } },
        { path: 'history/:taskId', name: 'history-detail', component: HistoryDetailPage, meta: { title: '历史详情', bodyClass: 'page-history' } },
        { path: 'chat', name: 'chat', component: ChatPage, meta: { title: 'AI 问答', bodyClass: 'page-chat', mainClass: 'site-main--chat' } },
        { path: 'education', alias: '/knowledge', name: 'education', component: KnowledgePage, meta: { title: '科普频道', bodyClass: 'page-education', mainClass: 'site-main--education' } },
        { path: 'quiz', name: 'quiz', component: QuizPage, meta: { title: '闯关答题', bodyClass: 'page-quiz', mainClass: 'site-main--quiz' } },
        { path: ':pathMatch(.*)*', name: 'not-found', component: NotFoundPage },
      ],
    },
  ],
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? '页面')} - 灵眸鉴真`
  document.body.className = `theme-containers-b ${String(to.meta.bodyClass ?? 'page-default')}`
})

export default router
