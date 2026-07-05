<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  Briefcase,
  CheckCircle2,
  Download,
  FileArchive,
  FileText,
  LogIn,
  LogOut,
  Plus,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Trash2,
  Upload,
  UserCheck,
  UserX,
  X,
  XCircle,
  UserPlus,
  Wand2,
} from 'lucide-vue-next'
import { api, clearToken, downloadWithToken, getToken, setToken } from './api'
import type {
  AdminLogItem,
  AdminUserItem,
  Award,
  Education,
  Intern,
  JobAnalyzeResponse,
  JobListItem,
  OptDTO,
  OptListItem,
  Project,
  ResumeDetail,
  ResumeListItem,
  TemplateItem,
  User,
} from './types'

type ReviewBlock = {
  key: string
  kind: 'skill' | 'project' | 'intern'
  title: string
  sourceId?: number | null
  segmentIndex?: number | null
  original: string
  optimized: string
  reason: string
  starBreakdown: string[]
  missingFacts: string[]
  changed: boolean
  accepted: boolean
}

type AppView = 'workspace' | 'admin'

const user = ref<User | null>(null)
const activeView = ref<AppView>('workspace')
const authMode = ref<'login' | 'register'>('login')
const authForm = ref({ account: '', password: '', email: '' })
const resumes = ref<ResumeListItem[]>([])
const activeResume = ref<ResumeDetail | null>(null)
const templates = ref<TemplateItem[]>([])
const jobs = ref<JobListItem[]>([])
const opts = ref<OptListItem[]>([])
const selectedOpt = ref<OptDTO | null>(null)
const selectedJobAnalysis = ref<JobAnalyzeResponse | null>(null)
const selectedTemplateId = ref<number | null>(null)
const selectedJobId = ref<number | null>(null)
const jobUrl = ref('')
const jobDescription = ref('')
const uploadFile = ref<File | null>(null)
const loading = ref(false)
const message = ref('')
const error = ref('')
const reviewModalOpen = ref(false)
const reviewBlocks = ref<ReviewBlock[]>([])
const adminUsers = ref<AdminUserItem[]>([])
const adminKeyword = ref('')
const adminStatus = ref<'ALL' | 'ACTIVE' | 'DISABLED'>('ALL')
const adminPage = ref(1)
const adminPageSize = 20
const adminTotal = ref(0)
const adminLogs = ref<AdminLogItem[]>([])
const logKeyword = ref('')
const logAction = ref('ALL')
const logPage = ref(1)
const logPageSize = 20
const logTotal = ref(0)
const templateUploadName = ref('')
const templateUploadFile = ref<File | null>(null)

const isAuthed = computed(() => Boolean(user.value && getToken()))
const isAdmin = computed(() => user.value?.role === 'ADMIN')
const activeTemplate = computed(() =>
  templates.value.find((item) => item.resumeTemplateId === selectedTemplateId.value),
)
const acceptedReviewCount = computed(() => reviewBlocks.value.filter((item) => item.accepted).length)
const selectedJobScore = computed(
  () => selectedJobAnalysis.value?.scoring?.globalScore ?? selectedJobAnalysis.value?.matchScore ?? null,
)
const adminTotalPages = computed(() => Math.max(1, Math.ceil(adminTotal.value / adminPageSize)))
const logTotalPages = computed(() => Math.max(1, Math.ceil(logTotal.value / logPageSize)))

watch(selectedJobId, async (jobId) => {
  if (!jobId) {
    selectedJobAnalysis.value = null
    return
  }
  await loadJobAnalysis(jobId)
})

onMounted(async () => {
  if (!getToken()) return
  try {
    user.value = await api.me()
    await loadWorkspace()
  } catch {
    clearToken()
    user.value = null
  }
})

async function run<T>(task: () => Promise<T>, success?: string): Promise<T | undefined> {
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const result = await task()
    if (success) message.value = success
    return result
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function submitAuth() {
  await run(async () => {
    if (authMode.value === 'register') {
      await api.register(authForm.value)
    }
    const login = await api.login({
      account: authForm.value.account,
      password: authForm.value.password,
    })
    setToken(login.token)
    user.value = login.user
    await loadWorkspace()
  }, '已登录')
}

function logout() {
  clearToken()
  user.value = null
  activeView.value = 'workspace'
  resumes.value = []
  activeResume.value = null
  selectedOpt.value = null
  adminUsers.value = []
  adminLogs.value = []
}

async function loadWorkspace() {
  const [resumePage, templateRows] = await Promise.all([api.listResumes(), api.listTemplates()])
  resumes.value = resumePage.items
  templates.value = templateRows
  if (!selectedTemplateId.value && templates.value.length) {
    selectedTemplateId.value = templates.value[0].resumeTemplateId
  }
  if (!activeResume.value && resumes.value.length) {
    await selectResume(resumes.value[0].resumeId)
  }
}

async function switchView(view: AppView) {
  activeView.value = view
  if (view === 'admin') {
    await Promise.all([loadAdminUsers(1), loadAdminLogs(1)])
  }
}

async function refreshCurrentView() {
  if (activeView.value === 'admin') {
    await Promise.all([loadAdminUsers(adminPage.value), loadAdminLogs(logPage.value)])
    return
  }
  await loadWorkspace()
}

async function loadAdminUsers(page = adminPage.value) {
  if (!isAdmin.value) return
  await run(async () => {
    adminPage.value = page
    const result = await api.listAdminUsers({
      keyword: adminKeyword.value.trim() || null,
      status: adminStatus.value === 'ALL' ? null : adminStatus.value,
      page,
      pageSize: adminPageSize,
    })
    adminUsers.value = result.items
    adminTotal.value = result.total
  }, '用户列表已刷新')
}

async function updateAdminUserStatus(row: AdminUserItem, status: 'ACTIVE' | 'DISABLED') {
  if (row.userId === user.value?.userId && status === 'DISABLED') {
    error.value = '不能在当前会话中禁用自己'
    return
  }
  await run(async () => {
    const updated =
      status === 'ACTIVE'
        ? await api.enableAdminUser(row.userId)
        : await api.disableAdminUser(row.userId)
    row.status = updated.status
    await loadAdminUsers(adminPage.value)
  }, status === 'ACTIVE' ? '用户已启用' : '用户已禁用')
}

async function loadAdminLogs(page = logPage.value) {
  if (!isAdmin.value) return
  await run(async () => {
    logPage.value = page
    const result = await api.listAdminLogs({
      keyword: logKeyword.value.trim() || null,
      action: logAction.value === 'ALL' ? null : logAction.value,
      page,
      pageSize: logPageSize,
    })
    adminLogs.value = result.items
    logTotal.value = result.total
  }, '日志列表已刷新')
}

function onTemplateFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  templateUploadFile.value = target.files?.[0] || null
}

async function uploadTemplate() {
  if (!templateUploadName.value.trim()) {
    error.value = '请输入模板名称'
    return
  }
  if (!templateUploadFile.value) {
    error.value = '请选择 .tex 或 .zip 模板文件'
    return
  }
  await run(async () => {
    const template = await api.uploadTemplate(templateUploadName.value.trim(), templateUploadFile.value as File)
    templates.value = await api.listTemplates()
    selectedTemplateId.value = template.resumeTemplateId
    templateUploadName.value = ''
    templateUploadFile.value = null
    await loadAdminLogs(1)
  }, '模板已上传')
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

async function refreshResumes() {
  await run(async () => {
    const page = await api.listResumes()
    resumes.value = page.items
  }, '简历列表已刷新')
}

async function selectResume(resumeId: number) {
  await run(async () => {
    activeResume.value = await api.getResume(resumeId)
    selectedOpt.value = null
    await loadResumeRelated(resumeId)
  })
}

async function deleteResume(resume: ResumeListItem) {
  const displayTitle = resume.title || `#${resume.resumeId}`
  if (!window.confirm(`确定删除简历「${displayTitle}」吗？删除后不会在列表中显示。`)) {
    return
  }

  await run(async () => {
    const wasActive = activeResume.value?.resumeId === resume.resumeId
    await api.deleteResume(resume.resumeId)
    const page = await api.listResumes()
    resumes.value = page.items

    if (!wasActive) return

    activeResume.value = null
    jobs.value = []
    opts.value = []
    selectedOpt.value = null
    selectedJobAnalysis.value = null
    selectedJobId.value = null
    reviewModalOpen.value = false
    reviewBlocks.value = []

    const nextResume = resumes.value[0]
    if (nextResume) {
      activeResume.value = await api.getResume(nextResume.resumeId)
      await loadResumeRelated(nextResume.resumeId)
    }
  }, '简历已删除')
}

async function loadResumeRelated(resumeId: number) {
  const [jobRows, optRows] = await Promise.all([api.listJobs(resumeId), api.listOpts(resumeId)])
  jobs.value = jobRows
  opts.value = optRows
  selectedJobId.value = jobRows[0]?.jobId ?? null
  if (selectedJobId.value) {
    await loadJobAnalysis(selectedJobId.value)
  } else {
    selectedJobAnalysis.value = null
  }
}

async function loadJobAnalysis(jobId: number) {
  try {
    selectedJobAnalysis.value = await api.getJob(jobId)
  } catch (err) {
    selectedJobAnalysis.value = null
    error.value = err instanceof Error ? err.message : String(err)
  }
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  uploadFile.value = target.files?.[0] || null
}

async function uploadResume() {
  if (!uploadFile.value) {
    error.value = '请选择 PDF 文件'
    return
  }
  await run(async () => {
    const result = await api.uploadPdf(uploadFile.value as File)
    activeResume.value = result.resume
    await refreshResumes()
    await loadResumeRelated(result.resumeId)
  }, 'PDF 已解析并生成简历')
}

async function saveResume() {
  if (!activeResume.value) return
  await run(async () => {
    await api.updateResume(activeResume.value!.resumeId, activeResume.value!)
    activeResume.value = await api.getResume(activeResume.value!.resumeId)
    await refreshResumes()
  }, '简历已保存')
}

async function analyzeJob() {
  const trimmedUrl = jobUrl.value.trim()
  const trimmedDescription = jobDescription.value.trim()
  if (!activeResume.value || (!trimmedUrl && !trimmedDescription)) {
    error.value = '请输入岗位 URL 或粘贴岗位描述'
    return
  }
  await run(async () => {
    const job = await api.analyzeJob(
      activeResume.value!.resumeId,
      trimmedUrl || null,
      trimmedDescription || null,
    )
    jobUrl.value = ''
    jobDescription.value = ''
    await loadResumeRelated(activeResume.value!.resumeId)
    selectedJobId.value = job.jobId
    selectedJobAnalysis.value = job
    if (job.status === 'BLOCKED') {
      message.value = '岗位页面被平台安全验证拦截，未进行匹配分析'
    } else if (job.status === 'EXPIRED') {
      message.value = '岗位页面已关闭或不可用，已停止分析'
    } else if (job.status === 'FAILED') {
      message.value = '岗位抓取失败，未进行匹配分析'
    } else {
      message.value = '岗位分析已完成'
    }
  })
}

async function optimizeResume() {
  if (!activeResume.value) return
  await run(async () => {
    const opt = await api.optimizeResume(activeResume.value!.resumeId, selectedJobId.value)
    selectedOpt.value = opt
    prepareReviewBlocks(opt)
    openReviewModal(opt)
    await loadResumeRelated(activeResume.value!.resumeId)
  }, '优化建议已生成')
}

async function openOpt(optId: number) {
  await run(async () => {
    const opt = await api.getOpt(optId)
    selectedOpt.value = opt
    prepareReviewBlocks(opt)
    openReviewModal(opt)
  })
}

function prepareReviewBlocks(opt: OptDTO) {
  reviewBlocks.value = buildReviewBlocks(opt)
}

async function applyOptimization() {
  if (!selectedOpt.value || !activeResume.value) return
  const acceptedBlocks = reviewBlocks.value.filter((item) => item.accepted)
  if (!acceptedBlocks.length) {
    error.value = '请至少确认一条优化建议'
    return
  }
  const acceptedProjectIds = acceptedBlocks
    .filter((item) => item.kind === 'project' && typeof item.sourceId === 'number')
    .map((item) => item.sourceId as number)
  const acceptedInternIds = acceptedBlocks
    .filter((item) => item.kind === 'intern' && typeof item.sourceId === 'number')
    .map((item) => item.sourceId as number)
  const projectSegmentIndexes = groupAcceptedSegments(acceptedBlocks, 'project')
  const internSegmentIndexes = groupAcceptedSegments(acceptedBlocks, 'intern')
  await run(async () => {
    await api.applyOpt(selectedOpt.value!.optId, {
      applySkill: acceptedBlocks.some((item) => item.kind === 'skill'),
      applyProjects: acceptedProjectIds.length > 0,
      applyInterns: acceptedInternIds.length > 0,
      projectIds: [...new Set(acceptedProjectIds)],
      internIds: [...new Set(acceptedInternIds)],
      projectSegmentIndexes: Object.keys(projectSegmentIndexes).length ? projectSegmentIndexes : null,
      internSegmentIndexes: Object.keys(internSegmentIndexes).length ? internSegmentIndexes : null,
    })
    activeResume.value = await api.getResume(activeResume.value!.resumeId)
    await loadResumeRelated(activeResume.value.resumeId)
    selectedOpt.value = await api.getOpt(selectedOpt.value!.optId)
    reviewBlocks.value = buildReviewBlocks(selectedOpt.value)
    reviewModalOpen.value = false
  }, '优化结果已写回简历')
}

function openReviewModal(opt: OptDTO) {
  selectedOpt.value = opt
  reviewBlocks.value = buildReviewBlocks(opt)
  if (!reviewBlocks.value.length) {
    error.value = '这条优化记录没有可逐项采纳的结构化结果，请重新生成优化'
    return
  }
  reviewModalOpen.value = true
}

function closeReviewModal() {
  reviewModalOpen.value = false
}

function setReviewAccepted(block: ReviewBlock, accepted: boolean) {
  block.accepted = accepted
}

function buildReviewBlocks(opt: OptDTO): ReviewBlock[] {
  const payload = opt.resultJson
  if (!payload) return []

  const blocks: ReviewBlock[] = []
  if (payload.skill?.optimized) {
    blocks.push({
      key: 'skill',
      kind: 'skill',
      title: '技能表达',
      sourceId: null,
      original: payload.skill.original || activeResume.value?.skillName || '',
      optimized: payload.skill.optimized,
      reason: payload.skill.reason,
      starBreakdown: [],
      missingFacts: payload.skill.missingFacts || [],
      changed: payload.skill.optimized !== (payload.skill.original || activeResume.value?.skillName || ''),
      accepted: true,
    })
  }

  for (const project of payload.projects || []) {
    if (!project.optimizedBullets?.length) continue
    const segments = project.segments || []
    if (segments.length) {
      for (const segment of segments) {
        blocks.push({
          key: `project-${project.sourceId ?? project.name}-${segment.segmentIndex}`,
          kind: 'project',
          title: `项目：${project.name} / 任务 ${segment.segmentIndex + 1}`,
          sourceId: project.sourceId,
          segmentIndex: segment.segmentIndex,
          original: segment.original,
          optimized: segment.optimized,
          reason: segment.reason || project.reason,
          starBreakdown: segment.starBreakdown || [],
          missingFacts: segment.missingFacts || project.missingFacts || [],
          changed: segment.changed,
          accepted: true,
        })
      }
    } else {
      blocks.push({
        key: `project-${project.sourceId ?? project.name}`,
        kind: 'project',
        title: `项目：${project.name}`,
        sourceId: project.sourceId,
        segmentIndex: null,
        original: project.original,
        optimized: project.optimizedBullets.map((item) => `- ${item}`).join('\n'),
        reason: project.reason,
        starBreakdown: project.starBreakdown || project.statBreakdown || [],
        missingFacts: project.missingFacts || [],
        changed: project.optimizedBullets.join('\n') !== project.original,
        accepted: true,
      })
    }
  }

  for (const intern of payload.interns || []) {
    if (!intern.optimizedBullets?.length) continue
    const segments = intern.segments || []
    if (segments.length) {
      for (const segment of segments) {
        blocks.push({
          key: `intern-${intern.sourceId ?? intern.name}-${segment.segmentIndex}`,
          kind: 'intern',
          title: `实习：${intern.name} / 任务 ${segment.segmentIndex + 1}`,
          sourceId: intern.sourceId,
          segmentIndex: segment.segmentIndex,
          original: segment.original,
          optimized: segment.optimized,
          reason: segment.reason || intern.reason,
          starBreakdown: segment.starBreakdown || [],
          missingFacts: segment.missingFacts || intern.missingFacts || [],
          changed: segment.changed,
          accepted: true,
        })
      }
    } else {
      blocks.push({
        key: `intern-${intern.sourceId ?? intern.name}`,
        kind: 'intern',
        title: `实习：${intern.name}`,
        sourceId: intern.sourceId,
        segmentIndex: null,
        original: intern.original,
        optimized: intern.optimizedBullets.map((item) => `- ${item}`).join('\n'),
        reason: intern.reason,
        starBreakdown: intern.starBreakdown || intern.statBreakdown || [],
        missingFacts: intern.missingFacts || [],
        changed: intern.optimizedBullets.join('\n') !== intern.original,
        accepted: true,
      })
    }
  }
  return blocks
}

function groupAcceptedSegments(blocks: ReviewBlock[], kind: 'project' | 'intern'): Record<number, number[]> {
  const grouped: Record<number, number[]> = {}
  for (const block of blocks) {
    if (block.kind !== kind || !block.accepted) continue
    if (typeof block.sourceId !== 'number' || typeof block.segmentIndex !== 'number') continue
    grouped[block.sourceId] ||= []
    grouped[block.sourceId].push(block.segmentIndex)
  }
  return grouped
}

async function generateLatex() {
  if (!activeResume.value || !selectedTemplateId.value) return
  await run(async () => {
    await api.generateLatex(activeResume.value!.resumeId, selectedTemplateId.value!)
  }, 'LaTeX zip 已生成')
}

async function downloadLatex() {
  if (!activeResume.value) return
  await run(async () => {
    const resumeId = activeResume.value!.resumeId
    await downloadWithToken(api.latexDownloadUrl(resumeId), `resume_${resumeId}.zip`)
  })
}

function addEducation() {
  activeResume.value?.educations.push({
    university: '',
    major: '',
    degree: '',
    startTime: '',
    endTime: '',
  })
}

function addProject() {
  activeResume.value?.projects.push({
    projectName: '',
    role: '',
    introduction: '',
    content: '',
    startTime: null,
    endTime: null,
  })
}

function addIntern() {
  activeResume.value?.interns.push({
    company: '',
    role: '',
    content: '',
    startTime: null,
    endTime: null,
  })
}

function addAward() {
  activeResume.value?.awards.push({
    name: '',
    awardTime: null,
  })
}

function removeItem<T>(items: T[], index: number) {
  items.splice(index, 1)
}
</script>

<template>
  <main class="app-shell">
    <section v-if="!isAuthed" class="auth-layout">
      <div class="auth-copy">
        <p class="eyebrow">Smart Resume Platform</p>
        <h1>智能简历工作台</h1>
        <p>解析 PDF、优化表达、套用 LaTeX 模板，并导出完整源码包。</p>
      </div>
      <form class="auth-panel" @submit.prevent="submitAuth">
        <div class="tabs">
          <button type="button" :class="{ active: authMode === 'login' }" @click="authMode = 'login'">
            <LogIn :size="16" /> 登录
          </button>
          <button type="button" :class="{ active: authMode === 'register' }" @click="authMode = 'register'">
            <UserPlus :size="16" /> 注册
          </button>
        </div>
        <label>
          账号
          <input v-model.trim="authForm.account" autocomplete="username" required />
        </label>
        <label v-if="authMode === 'register'">
          邮箱
          <input v-model.trim="authForm.email" type="email" autocomplete="email" required />
        </label>
        <label>
          密码
          <input v-model="authForm.password" type="password" autocomplete="current-password" required />
        </label>
        <button class="primary" type="submit" :disabled="loading">
          <LogIn :size="17" /> {{ authMode === 'login' ? '登录' : '注册并登录' }}
        </button>
      </form>
    </section>

    <template v-else>
      <header class="topbar">
        <div>
          <p class="eyebrow">Smart Resume Platform</p>
          <h1>简历生成工作台</h1>
        </div>
        <div class="topbar-actions">
          <span>{{ user?.account }}</span>
          <div class="view-switch" v-if="isAdmin">
            <button class="ghost" :class="{ active: activeView === 'workspace' }" @click="switchView('workspace')">
              <FileText :size="16" /> 工作台
            </button>
            <button class="ghost" :class="{ active: activeView === 'admin' }" @click="switchView('admin')">
              <ShieldCheck :size="16" /> 管理员
            </button>
          </div>
          <button class="ghost" @click="refreshCurrentView" :disabled="loading">
            <RefreshCw :size="16" /> 刷新
          </button>
          <button class="ghost" @click="logout">
            <LogOut :size="16" /> 退出
          </button>
        </div>
      </header>

      <div class="status-line" v-if="message || error || loading">
        <span v-if="loading">处理中...</span>
        <span v-if="message" class="ok">{{ message }}</span>
        <span v-if="error" class="bad">{{ error }}</span>
      </div>

      <section v-if="activeView === 'workspace'" class="workspace-grid">
        <aside class="sidebar">
          <div class="section-head">
            <h2>简历</h2>
            <button class="icon-button" @click="refreshResumes" title="刷新简历">
              <RefreshCw :size="16" />
            </button>
          </div>
          <label class="upload-box">
            <Upload :size="18" />
            <span>{{ uploadFile?.name || '选择 PDF' }}</span>
            <input type="file" accept="application/pdf" @change="onFileChange" />
          </label>
          <button class="primary full" @click="uploadResume" :disabled="loading">
            <FileText :size="17" /> 上传解析
          </button>

          <div class="list">
            <div
              v-for="resume in resumes"
              :key="resume.resumeId"
              class="list-item resume-list-item"
              :class="{ active: activeResume?.resumeId === resume.resumeId }"
            >
              <button class="resume-select" type="button" @click="selectResume(resume.resumeId)">
                <span>{{ resume.title }}</span>
                <small>{{ resume.status }}</small>
              </button>
              <button
                class="icon-button danger resume-delete"
                type="button"
                :disabled="loading"
                title="删除简历"
                aria-label="删除简历"
                @click.stop="deleteResume(resume)"
              >
                <Trash2 :size="15" />
              </button>
            </div>
          </div>
        </aside>

        <section class="editor" v-if="activeResume">
          <div class="section-head">
            <h2>简历内容</h2>
            <button class="primary" @click="saveResume" :disabled="loading">
              <Save :size="16" /> 保存
            </button>
          </div>

          <div class="form-grid compact">
            <label>标题<input v-model="activeResume.title" /></label>
            <label>姓名<input v-model="activeResume.name" /></label>
            <label>年龄<input v-model.number="activeResume.age" type="number" min="0" max="120" /></label>
            <label>邮箱<input v-model="activeResume.email" /></label>
            <label>电话<input v-model="activeResume.phone" /></label>
            <label>期望岗位<input v-model="activeResume.expectedPosition" /></label>
            <label>期望薪资<input v-model="activeResume.expectedSalary" /></label>
          </div>

          <label class="block-field">
            技能
            <textarea v-model="activeResume.skillName" rows="4" />
          </label>
          <label class="block-field">
            个人简介
            <textarea v-model="activeResume.personalContext" rows="4" />
          </label>

          <div class="detail-section">
            <div class="section-head small">
              <h3>教育背景</h3>
              <button class="ghost" @click="addEducation"><Plus :size="15" /> 添加</button>
            </div>
            <div v-for="(edu, index) in activeResume.educations" :key="edu.educationInfoId || index" class="row-editor">
              <input v-model="edu.university" placeholder="学校" />
              <input v-model="edu.major" placeholder="专业" />
              <input v-model="edu.degree" placeholder="学历" />
              <input v-model="edu.startTime" type="date" />
              <input v-model="edu.endTime" type="date" />
              <button class="icon-button danger" @click="removeItem(activeResume.educations, index)" title="删除">
                <Trash2 :size="15" />
              </button>
            </div>
          </div>

          <div class="detail-section">
            <div class="section-head small">
              <h3>项目经历</h3>
              <button class="ghost" @click="addProject"><Plus :size="15" /> 添加</button>
            </div>
            <div v-for="(project, index) in activeResume.projects" :key="project.projectInfoId || index" class="experience-editor">
              <div class="form-grid compact">
                <label>项目名<input v-model="project.projectName" /></label>
                <label>角色<input v-model="project.role" /></label>
                <label>开始<input v-model="project.startTime" type="date" /></label>
                <label>结束<input v-model="project.endTime" type="date" /></label>
              </div>
              <label class="block-field">简介<textarea v-model="project.introduction" rows="2" /></label>
              <label class="block-field">内容<textarea v-model="project.content" rows="4" /></label>
              <button class="ghost danger-text" @click="removeItem(activeResume.projects, index)">
                <Trash2 :size="15" /> 删除项目
              </button>
            </div>
          </div>

          <div class="detail-section">
            <div class="section-head small">
              <h3>实习经历</h3>
              <button class="ghost" @click="addIntern"><Plus :size="15" /> 添加</button>
            </div>
            <div v-for="(intern, index) in activeResume.interns" :key="intern.internInfoId || index" class="experience-editor">
              <div class="form-grid compact">
                <label>公司<input v-model="intern.company" /></label>
                <label>角色<input v-model="intern.role" /></label>
                <label>开始<input v-model="intern.startTime" type="date" /></label>
                <label>结束<input v-model="intern.endTime" type="date" /></label>
              </div>
              <label class="block-field">内容<textarea v-model="intern.content" rows="4" /></label>
              <button class="ghost danger-text" @click="removeItem(activeResume.interns, index)">
                <Trash2 :size="15" /> 删除实习
              </button>
            </div>
          </div>

          <div class="detail-section">
            <div class="section-head small">
              <h3>获奖情况</h3>
              <button class="ghost" @click="addAward"><Plus :size="15" /> 添加</button>
            </div>
            <div v-for="(award, index) in activeResume.awards" :key="award.awardInfoId || index" class="row-editor">
              <input v-model="award.name" placeholder="奖项名称" />
              <input v-model="award.awardTime" type="date" />
              <button class="icon-button danger" @click="removeItem(activeResume.awards, index)" title="删除">
                <Trash2 :size="15" />
              </button>
            </div>
          </div>
        </section>

        <aside class="action-panel" v-if="activeResume">
          <section class="tool-band">
            <h2>岗位与优化</h2>
            <div class="inline-action">
              <input v-model.trim="jobUrl" placeholder="岗位 URL" />
              <button class="ghost" @click="analyzeJob" :disabled="loading">
                <Briefcase :size="16" /> 分析
              </button>
            </div>
            <label class="job-description-field">
              岗位描述
              <textarea
                v-model="jobDescription"
                rows="8"
                placeholder="粘贴岗位职责、任职要求、薪资地点等 JD 内容"
              />
            </label>
            <label>
              关联岗位
              <select v-model.number="selectedJobId">
                <option :value="null">不关联岗位</option>
                <option v-for="job in jobs" :key="job.jobId" :value="job.jobId">
                  {{ job.jobName || `岗位 ${job.jobId}` }} {{ job.company ? `- ${job.company}` : '' }}
                </option>
              </select>
            </label>
            <div v-if="selectedJobAnalysis" class="job-analysis-panel">
              <div class="section-head small">
                <h2>岗位分析</h2>
                <span class="score">{{ selectedJobScore !== null ? selectedJobScore.toFixed(1) : '-' }}</span>
              </div>
              <div class="job-meta">
                <span>{{ selectedJobAnalysis.status }}</span>
                <span>{{ selectedJobAnalysis.suitable ? '建议投递' : '谨慎投递' }}</span>
                <span v-if="selectedJobAnalysis.jobArchetype">{{ selectedJobAnalysis.jobArchetype }}</span>
              </div>
              <p v-if="selectedJobAnalysis.jobSummary.tldr" class="analysis-summary">
                {{ selectedJobAnalysis.jobSummary.tldr }}
              </p>
              <p v-if="selectedJobAnalysis.analysis" class="analysis-text">
                {{ selectedJobAnalysis.analysis }}
              </p>
              <div class="analysis-facts">
                <span v-if="selectedJobAnalysis.jobSummary.seniority">资历：{{ selectedJobAnalysis.jobSummary.seniority }}</span>
                <span v-if="selectedJobAnalysis.jobSummary.workMode">模式：{{ selectedJobAnalysis.jobSummary.workMode }}</span>
                <span v-if="selectedJobAnalysis.levelStrategy.inferredLevel">职级：{{ selectedJobAnalysis.levelStrategy.inferredLevel }}</span>
              </div>
              <div v-if="selectedJobAnalysis.scoring.dimensions.length" class="analysis-block">
                <strong>评分维度</strong>
                <ul>
                  <li v-for="item in selectedJobAnalysis.scoring.dimensions" :key="item.name">
                    {{ item.name }}：{{ item.score ?? '-' }} - {{ item.rationale }}
                  </li>
                </ul>
              </div>
              <div v-if="selectedJobAnalysis.resumeMatch.mappings.length" class="analysis-block">
                <strong>匹配证据</strong>
                <div
                  v-for="(item, index) in selectedJobAnalysis.resumeMatch.mappings.slice(0, 4)"
                  :key="`${item.requirement}-${index}`"
                  class="mapping-item"
                >
                  <b>{{ item.requirement }}</b>
                  <p v-if="item.resumeEvidence.length">证据：{{ item.resumeEvidence.join('；') }}</p>
                  <p v-if="item.gap">缺口：{{ item.gap }}</p>
                  <p v-if="item.remedy">补救：{{ item.remedy }}</p>
                </div>
              </div>
              <div v-if="selectedJobAnalysis.optimizationFocus.length" class="analysis-block">
                <strong>简历优化重点</strong>
                <ul>
                  <li v-for="item in selectedJobAnalysis.optimizationFocus" :key="item">{{ item }}</li>
                </ul>
              </div>
              <div
                v-if="selectedJobAnalysis.authenticityCheck.redFlags.length || selectedJobAnalysis.authenticityCheck.stopReason"
                class="analysis-block warning"
              >
                <strong>真实性检查</strong>
                <p v-if="selectedJobAnalysis.authenticityCheck.stopReason">
                  {{ selectedJobAnalysis.authenticityCheck.stopReason }}
                </p>
                <ul v-if="selectedJobAnalysis.authenticityCheck.redFlags.length">
                  <li v-for="item in selectedJobAnalysis.authenticityCheck.redFlags" :key="item">{{ item }}</li>
                </ul>
              </div>
            </div>
            <button class="primary full" @click="optimizeResume" :disabled="loading">
              <Wand2 :size="17" /> 生成优化建议
            </button>
            <div class="list condensed">
              <button
                v-for="opt in opts"
                :key="opt.optId"
                class="list-item"
                :class="{ active: selectedOpt?.optId === opt.optId }"
                @click="openOpt(opt.optId)"
              >
                <span>优化 #{{ opt.optId }}</span>
                <small>{{ opt.score ?? '-' }} / {{ opt.status }}</small>
              </button>
            </div>
          </section>

          <section class="tool-band" v-if="selectedOpt">
            <div class="section-head small">
              <h2>优化审阅</h2>
              <span class="score">{{ selectedOpt.score ?? '-' }}</span>
            </div>
            <p class="tool-note">
              共 {{ reviewBlocks.length }} 条可采纳建议，打开弹框逐条查看前后对比。
            </p>
            <button class="primary full" @click="openReviewModal(selectedOpt)" :disabled="loading">
              <Wand2 :size="17" /> 打开优化弹框
            </button>
          </section>

          <section class="tool-band">
            <h2>LaTeX 模板</h2>
            <label>
              模板
              <select v-model.number="selectedTemplateId">
                <option v-for="template in templates" :key="template.resumeTemplateId" :value="template.resumeTemplateId">
                  {{ template.templateName }}
                </option>
              </select>
            </label>
            <p class="template-path">{{ activeTemplate?.latex }}</p>
            <div class="button-row">
              <button class="primary" @click="generateLatex" :disabled="loading || !selectedTemplateId">
                <FileArchive :size="17" /> 生成
              </button>
              <button class="ghost" @click="downloadLatex" :disabled="loading">
                <Download :size="17" /> 下载
              </button>
            </div>
          </section>
        </aside>
      </section>

      <section v-else-if="isAdmin" class="admin-layout">
        <section class="admin-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">User Management</p>
              <h2>用户状态管理</h2>
            </div>
            <button class="ghost" @click="loadAdminUsers(1)" :disabled="loading">
              <RefreshCw :size="16" /> 刷新用户
            </button>
          </div>

          <div class="admin-toolbar">
            <label>
              搜索
              <div class="inline-action">
                <input v-model.trim="adminKeyword" placeholder="账号或邮箱" @keyup.enter="loadAdminUsers(1)" />
                <button class="ghost" @click="loadAdminUsers(1)" :disabled="loading">
                  <Search :size="16" /> 查询
                </button>
              </div>
            </label>
            <label>
              状态
              <select v-model="adminStatus" @change="loadAdminUsers(1)">
                <option value="ALL">全部</option>
                <option value="ACTIVE">启用</option>
                <option value="DISABLED">禁用</option>
              </select>
            </label>
          </div>

          <div class="admin-table">
            <div class="admin-table-head user-grid">
              <span>账号</span>
              <span>邮箱</span>
              <span>角色</span>
              <span>状态</span>
              <span>最近登录</span>
              <span>操作</span>
            </div>
            <div v-for="row in adminUsers" :key="row.userId" class="admin-table-row user-grid">
              <span class="strong">{{ row.account }}</span>
              <span>{{ row.email || '-' }}</span>
              <span>{{ row.role }}</span>
              <span>
                <mark class="status-pill" :class="row.status.toLowerCase()">{{ row.status }}</mark>
              </span>
              <span>{{ formatDateTime(row.lastLoginTime) }}</span>
              <span class="row-actions">
                <button
                  v-if="row.status !== 'ACTIVE'"
                  class="ghost"
                  @click="updateAdminUserStatus(row, 'ACTIVE')"
                  :disabled="loading"
                >
                  <UserCheck :size="15" /> 启用
                </button>
                <button
                  v-else
                  class="ghost danger-text"
                  @click="updateAdminUserStatus(row, 'DISABLED')"
                  :disabled="loading || row.userId === user?.userId"
                >
                  <UserX :size="15" /> 禁用
                </button>
              </span>
            </div>
            <p v-if="!adminUsers.length" class="empty-note">暂无匹配用户</p>
          </div>

          <div class="pager">
            <button class="ghost" @click="loadAdminUsers(adminPage - 1)" :disabled="loading || adminPage <= 1">上一页</button>
            <span>第 {{ adminPage }} / {{ adminTotalPages }} 页，共 {{ adminTotal }} 人</span>
            <button class="ghost" @click="loadAdminUsers(adminPage + 1)" :disabled="loading || adminPage >= adminTotalPages">下一页</button>
          </div>
        </section>

        <section class="admin-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">Template Upload</p>
              <h2>上传 LaTeX 模板</h2>
            </div>
            <FileArchive :size="22" />
          </div>
          <div class="template-upload-grid">
            <label>
              模板名称
              <input v-model.trim="templateUploadName" placeholder="例如：校园简洁模板" />
            </label>
            <label class="upload-box compact-upload">
              <Upload :size="18" />
              <span>{{ templateUploadFile?.name || '选择 .tex 或 .zip 文件' }}</span>
              <input type="file" accept=".tex,.zip,application/zip" @change="onTemplateFileChange" />
            </label>
            <button class="primary" @click="uploadTemplate" :disabled="loading">
              <Upload :size="17" /> 上传模板
            </button>
          </div>
          <div class="template-list">
            <div v-for="template in templates" :key="template.resumeTemplateId" class="template-row">
              <span>{{ template.templateName }}</span>
              <small>{{ template.latex }}</small>
            </div>
          </div>
        </section>

        <section class="admin-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">Audit Logs</p>
              <h2>系统操作日志</h2>
            </div>
            <button class="ghost" @click="loadAdminLogs(1)" :disabled="loading">
              <RefreshCw :size="16" /> 刷新日志
            </button>
          </div>

          <div class="admin-toolbar">
            <label>
              搜索
              <div class="inline-action">
                <input v-model.trim="logKeyword" placeholder="操作、对象或详情" @keyup.enter="loadAdminLogs(1)" />
                <button class="ghost" @click="loadAdminLogs(1)" :disabled="loading">
                  <Search :size="16" /> 查询
                </button>
              </div>
            </label>
            <label>
              类型
              <select v-model="logAction" @change="loadAdminLogs(1)">
                <option value="ALL">全部</option>
                <option value="REGISTER">用户注册</option>
                <option value="LOGIN">用户登录</option>
                <option value="UPLOAD_RESUME">上传简历</option>
                <option value="UPDATE_RESUME">保存简历</option>
                <option value="DELETE_RESUME">删除简历</option>
                <option value="GENERATE_LATEX">生成 LaTeX</option>
                <option value="DOWNLOAD_LATEX">下载 LaTeX</option>
                <option value="ANALYZE_JOB">岗位分析</option>
                <option value="OPTIMIZE_RESUME">生成优化</option>
                <option value="APPLY_OPTIMIZATION">采纳优化</option>
                <option value="UPDATE_OPT_STATUS">更新优化状态</option>
                <option value="DISABLE_USER">禁用用户</option>
                <option value="ENABLE_USER">启用用户</option>
                <option value="UPLOAD_TEMPLATE">上传模板</option>
              </select>
            </label>
          </div>

          <div class="admin-table">
            <div class="admin-table-head log-grid">
              <span>时间</span>
              <span>操作</span>
              <span>对象</span>
              <span>详情</span>
              <span>IP</span>
            </div>
            <div v-for="row in adminLogs" :key="row.logId" class="admin-table-row log-grid">
              <span>{{ formatDateTime(row.createdAt) }}</span>
              <span>{{ row.action }}</span>
              <span>{{ row.targetType || '-' }} {{ row.targetId || '' }}</span>
              <span>{{ row.detail || '-' }}</span>
              <span>{{ row.ip || '-' }}</span>
            </div>
            <p v-if="!adminLogs.length" class="empty-note">暂无操作日志</p>
          </div>

          <div class="pager">
            <button class="ghost" @click="loadAdminLogs(logPage - 1)" :disabled="loading || logPage <= 1">上一页</button>
            <span>第 {{ logPage }} / {{ logTotalPages }} 页，共 {{ logTotal }} 条</span>
            <button class="ghost" @click="loadAdminLogs(logPage + 1)" :disabled="loading || logPage >= logTotalPages">下一页</button>
          </div>
        </section>
      </section>

      <div v-if="reviewModalOpen && selectedOpt" class="modal-backdrop">
        <section class="review-modal" role="dialog" aria-modal="true" aria-labelledby="review-title">
          <header class="modal-header">
            <div>
              <p class="eyebrow">Optimization Review</p>
              <h2 id="review-title">逐项确认优化建议</h2>
            </div>
            <button class="icon-button" @click="closeReviewModal" title="关闭">
              <X :size="18" />
            </button>
          </header>

          <div class="modal-summary">
            <span>评分：{{ selectedOpt.score ?? '-' }}</span>
            <span>已确认：{{ acceptedReviewCount }} / {{ reviewBlocks.length }}</span>
            <span>状态：{{ selectedOpt.status }}</span>
          </div>

          <div class="review-list">
            <article
              v-for="block in reviewBlocks"
              :key="block.key"
              class="review-card"
              :class="{ declined: !block.accepted }"
            >
              <div class="review-card-head">
                <div>
                  <span class="review-kind">{{ block.kind === 'skill' ? '技能' : block.kind === 'project' ? '项目' : '实习' }}</span>
                  <h3>{{ block.title }}</h3>
                </div>
                <span class="review-state" :class="{ accepted: block.accepted }">
                  {{ !block.changed ? '建议保留' : block.accepted ? '已确认' : '已取消' }}
                </span>
              </div>

              <div class="diff-grid">
                <div class="diff-pane before">
                  <strong>优化前</strong>
                  <pre>{{ block.original || '原文为空' }}</pre>
                </div>
                <div class="diff-pane after">
                  <strong>优化后</strong>
                  <pre>{{ block.optimized }}</pre>
                </div>
              </div>

              <div class="reason-box">
                <strong>为什么这么优化</strong>
                <p>{{ block.reason || 'Agent 未返回明确原因。' }}</p>
                <ul v-if="block.starBreakdown.length">
                  <li v-for="entry in block.starBreakdown" :key="entry">{{ entry }}</li>
                </ul>
                <p v-if="block.missingFacts.length" class="missing-facts">
                  建议补充：{{ block.missingFacts.join('；') }}
                </p>
              </div>

              <div class="review-actions">
                <button class="primary" @click="setReviewAccepted(block, true)">
                  <CheckCircle2 :size="16" /> 确认这一项
                </button>
                <button class="ghost danger-text" @click="setReviewAccepted(block, false)">
                  <XCircle :size="16" /> 取消这一项
                </button>
              </div>
            </article>
          </div>

          <footer class="modal-footer">
            <button class="ghost" @click="closeReviewModal">先不写回</button>
            <button class="primary" @click="applyOptimization" :disabled="loading || acceptedReviewCount === 0">
              <CheckCircle2 :size="17" /> 写回已确认项
            </button>
          </footer>
        </section>
      </div>
    </template>
  </main>
</template>
