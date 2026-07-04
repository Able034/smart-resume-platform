export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface User {
  userId: number
  account: string
  email?: string | null
  role: string
  status: string
}

export interface LoginResponse {
  token: string
  user: User
}

export interface PageData<T> {
  items: T[]
  page: number
  pageSize: number
  total: number
}

export interface ResumeListItem {
  resumeId: number
  title: string
  status: string
  updatedAt?: string | null
}

export interface Education {
  educationInfoId?: number | null
  university: string
  major: string
  degree: string
  startTime: string
  endTime?: string | null
}

export interface Project {
  projectInfoId?: number | null
  projectName: string
  role?: string | null
  introduction?: string | null
  content: string
  startTime?: string | null
  endTime?: string | null
}

export interface Intern {
  internInfoId?: number | null
  company: string
  role?: string | null
  content: string
  startTime?: string | null
  endTime?: string | null
}

export interface Award {
  awardInfoId?: number | null
  name: string
  awardTime?: string | null
}

export interface ResumeDetail {
  resumeId: number
  userId: number
  resumeTemplateId?: number | null
  title: string
  name?: string | null
  age?: number | null
  email?: string | null
  phone?: string | null
  expectedSalary?: string | null
  expectedPosition?: string | null
  skillName: string
  personalContext: string
  status: string
  createdAt?: string | null
  updatedAt?: string | null
  educations: Education[]
  projects: Project[]
  interns: Intern[]
  awards: Award[]
}

export interface UploadResponse {
  resumeId: number
  parseStatus: string
  resume: ResumeDetail
}

export interface TemplateItem {
  resumeTemplateId: number
  templateName: string
  latex: string
  previewUrl?: string | null
  status: string
}

export interface LatexResponse {
  resumeId: number
  resumeTemplateId: number
  latexFileName: string
  zipFileName: string
  downloadUrl: string
  warnings: string[]
}

export interface JobListItem {
  jobId: number
  jobName?: string | null
  company?: string | null
  status: string
  createdAt?: string | null
}

export interface JobSummary {
  jobType: string
  domain: string
  function: string
  seniority: string
  workMode: string
  tldr: string
}

export interface RequirementMapping {
  requirement: string
  importance: string
  resumeEvidence: string[]
  gap: string
  remedy: string
}

export interface ResumeMatchAnalysis {
  keyMatches: string[]
  mappings: RequirementMapping[]
  gaps: string[]
  remedies: string[]
}

export interface LevelStrategy {
  inferredLevel: string
  levelSignals: string[]
  positioning: string
  honestSeniorityPitch: string[]
  risks: string[]
}

export interface CompensationMarket {
  salaryRange: string
  compensationReputation: string
  marketDemand: string
  evidence: string[]
  unknowns: string[]
}

export interface CustomizationPlan {
  resumeChanges: string[]
  linkedinChanges: string[]
  keywordFocus: string[]
  rewriteFocus: string[]
}

export interface InterviewStoryPrompt {
  requirement: string
  storyAngle: string
  resumeEvidence: string
  starROutline: string[]
  missingFacts: string[]
}

export interface InterviewPlan {
  starStoryPrompts: InterviewStoryPrompt[]
  likelyQuestions: string[]
  prepTasks: string[]
}

export interface JobAuthenticityCheck {
  verdict: string
  confidence: string
  activeSignals: string[]
  redFlags: string[]
  stopReason: string
}

export interface ScoreDimension {
  name: string
  score?: number | null
  weight?: number | null
  rationale: string
}

export interface JobScoring {
  dimensions: ScoreDimension[]
  globalScore?: number | null
  recommendation: string
  scoreBand: string
}

export interface JobAnalyzeResponse extends JobListItem {
  resumeId: number
  jobUrl: string
  content: string
  matchScore?: number | null
  suitable?: boolean | null
  confidenceSource: string[]
  analysis: string
  jobArchetype: string
  jobSummary: JobSummary
  resumeMatch: ResumeMatchAnalysis
  levelStrategy: LevelStrategy
  compensationMarket: CompensationMarket
  customizationPlan: CustomizationPlan
  interviewPlan: InterviewPlan
  authenticityCheck: JobAuthenticityCheck
  scoring: JobScoring
  optimizationFocus: string[]
  starStoryFocus: string[]
  resumeRewriteFocus: string[]
}

export interface TextOptimization {
  original: string
  optimized: string
  reason: string
  missingFacts: string[]
}

export interface SegmentOptimization {
  segmentIndex: number
  original: string
  optimized: string
  changed: boolean
  reason: string
  starBreakdown: string[]
  missingFacts: string[]
}

export interface ExperienceOptimization {
  sourceId?: number | null
  name: string
  role?: string | null
  original: string
  starBreakdown: string[]
  statBreakdown?: string[]
  optimizedBullets: string[]
  segments: SegmentOptimization[]
  reason: string
  missingFacts: string[]
}

export interface OptimizationPayload {
  summary: string
  score?: number | null
  skill: TextOptimization
  projects: ExperienceOptimization[]
  interns: ExperienceOptimization[]
  warnings: string[]
}

export interface OptDTO {
  optId: number
  resumeId: number
  jobId?: number | null
  content: string
  resultJson?: OptimizationPayload | null
  score?: number | null
  status: string
  createdAt?: string | null
}

export interface OptListItem {
  optId: number
  jobId?: number | null
  score?: number | null
  status: string
  createdAt?: string | null
}

export interface ApplyOptimizationResponse {
  optId: number
  resumeId: number
  appliedSkill: boolean
  appliedProjectIds: number[]
  appliedInternIds: number[]
  status: string
}
