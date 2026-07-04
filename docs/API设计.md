# API 设计

本文档根据精简版数据库设计、领域模型和系统操作契约整理后端 API。接口采用 REST 风格，路径统一使用 `/api/v1` 前缀，数据格式使用 JSON，PDF 上传使用 `multipart/form-data`。

## 设计口径

系统第一版围绕以下核心流程设计：

1. 用户注册登录。
2. 用户上传 PDF 简历。
3. 系统抽取 PDF 字符串文本。
4. 简历解析 Agent 将字符串解析为标准 Pydantic 对象。
5. 系统把解析结果保存到 `resume`、`education_info`、`project_info`、`intern_info`、`award_info`。
6. 用户校对并保存简历信息。
7. 用户选择系统预置 LaTeX 模板。
8. 模板 Agent 读取简历信息和模板 LaTeX 文件，生成可下载的 LaTeX 代码。
9. 用户提交 Boss 直聘等岗位 URL。
10. 系统抓取岗位内容，保存到 `job`，岗位分析 Agent 输出匹配度、是否合适和置信来源。
11. 简历优化 Agent 基于真实简历内容生成优化建议，保存到 `opt`，不虚构经历、数据和成果。

第一版不扩展额外的版本、任务、报告和日志持久化表，避免和精简数据库设计不一致。

## 通用约定

### 基础地址

```text
http://localhost:8080/api/v1
```

### 认证方式

```http
Authorization: Bearer <token>
```

### 统一响应格式

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

失败响应：

```json
{
  "code": 40001,
  "message": "参数不合法",
  "data": null
}
```

分页响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "page": 1,
    "pageSize": 10,
    "total": 0
  }
}
```

### 通用状态码

| code | 含义 |
|---:|---|
| 0 | 成功 |
| 40001 | 请求参数不合法 |
| 40101 | 未登录或登录已过期 |
| 40301 | 无权限 |
| 40401 | 资源不存在 |
| 40901 | 数据冲突，如账号重复 |
| 50001 | 系统内部错误 |

## 接口总览

| 用例 | 接口组 | 主要接口 |
|---|---|---|
| UC-01 用户注册与登录 | 认证接口 | 注册、登录、获取当前用户 |
| UC-02 PDF 简历解析入库 | PDF 简历接口 | 上传 PDF、解析入库 |
| UC-03 用户校对与编辑简历 | 简历接口 | 查询简历详情、保存校对结果、删除简历 |
| UC-04 选择模板并生成 LaTeX 简历 | 模板/生成接口 | 查询模板、生成 LaTeX 代码下载链接 |
| UC-05 岗位 URL 解析与匹配分析 | 岗位接口 | 提交岗位 URL、查询岗位分析结果 |
| UC-06 简历优化建议 | 优化接口 | 生成优化建议、标记建议使用状态 |
| UC-07 管理用户账号 | 管理员用户接口 | 用户列表、搜索用户、禁用/启用用户 |

## 数据结构

### ResumeDetail

```json
{
  "resumeId": 1001,
  "userId": 1,
  "resumeTemplateId": 1,
  "title": "Java 后端开发简历",
  "skillName": "Java, Spring Boot, MySQL, Redis",
  "personalContext": "本人具备扎实的 Java 后端开发基础...",
  "status": "SAVED",
  "educations": [
    {
      "educationInfoId": 11,
      "university": "示例大学",
      "major": "软件工程",
      "degree": "本科",
      "startTime": "2022-09-01",
      "endTime": "2026-06-30"
    }
  ],
  "projects": [
    {
      "projectInfoId": 21,
      "projectName": "智能简历平台",
      "role": "后端开发",
      "introduction": "面向求职者的简历解析与优化系统",
      "content": "负责 PDF 解析、Agent 调用和 MySQL 落库接口设计。",
      "startTime": "2026-03-01",
      "endTime": "2026-06-30"
    }
  ],
  "interns": [
    {
      "internInfoId": 31,
      "company": "示例科技有限公司",
      "role": "Java 开发实习生",
      "content": "参与业务接口开发和数据库表设计。",
      "startTime": "2025-07-01",
      "endTime": "2025-09-01"
    }
  ],
  "awards": [
    {
      "awardInfoId": 41,
      "name": "校级程序设计竞赛二等奖",
      "awardTime": "2025-05-01"
    }
  ]
}
```

## UC-01 用户注册与登录

### POST /auth/register

对应 SOC-02 `submitRegisterInfo(account, password, email)`。

请求：

```json
{
  "account": "zhangsan",
  "password": "123456",
  "email": "zhangsan@example.com"
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "userId": 1,
    "account": "zhangsan",
    "email": "zhangsan@example.com",
    "role": "USER",
    "status": "ACTIVE"
  }
}
```

校验规则：

- `account` 必填，长度 4 到 50，唯一。
- `password` 必填，长度不少于 6。
- `email` 必填，格式合法，唯一。

### POST /auth/login

对应 SOC-03 `submitLoginInfo(account, password)`。

请求：

```json
{
  "account": "zhangsan",
  "password": "123456"
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "jwt-token",
    "user": {
      "userId": 1,
      "account": "zhangsan",
      "role": "USER",
      "status": "ACTIVE"
    }
  }
}
```

### GET /auth/me

获取当前登录用户。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "userId": 1,
    "account": "zhangsan",
    "email": "zhangsan@example.com",
    "role": "USER",
    "status": "ACTIVE"
  }
}
```

## UC-02 PDF 简历解析入库

### POST /resumes/upload-pdf

对应 SOC-05 `uploadPDFResume(pdfFile)`。

请求：

```http
Content-Type: multipart/form-data
Authorization: Bearer <token>

file=<resume.pdf>
```

处理过程：

- 校验 PDF 文件格式和大小。
- 抽取 PDF 字符串文本。
- 调用 `ResumeParseAgent`。
- Agent 输出标准 Pydantic 对象。
- Pydantic 校验通过后写入 MySQL。
- 写入 `resume`、`education_info`、`project_info`、`intern_info`、`award_info`。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "resumeId": 1001,
    "parseStatus": "PARSED",
    "resume": {
      "resumeId": 1001,
      "title": "PDF 导入简历",
      "skillName": "Java, Spring Boot, MySQL",
      "personalContext": "热爱后端开发，熟悉 Java 技术栈。",
      "status": "DRAFT",
      "educations": [],
      "projects": [],
      "interns": [],
      "awards": []
    }
  }
}
```

失败响应示例：

```json
{
  "code": 40001,
  "message": "PDF 解析失败，未识别到有效简历内容",
  "data": {
    "parseStatus": "FAILED"
  }
}
```

## UC-03 用户校对与编辑简历

### GET /resumes

查询当前用户简历列表。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `keyword` | `string` | 否 | 按标题搜索 |
| `status` | `string` | 否 | `DRAFT`、`SAVED`、`ARCHIVED` |
| `page` | `int` | 否 | 页码，默认 1 |
| `pageSize` | `int` | 否 | 每页数量，默认 10 |

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "resumeId": 1001,
        "title": "Java 后端开发简历",
        "status": "SAVED",
        "updatedAt": "2026-07-01T10:00:00"
      }
    ],
    "page": 1,
    "pageSize": 10,
    "total": 1
  }
}
```

### GET /resumes/{resumeId}

对应 SOC-06 `selectResumeForCheck(resumeId)`。

响应：返回 `ResumeDetail`。

权限规则：

- 只能查询当前用户自己的简历。

### PUT /resumes/{resumeId}

对应 SOC-07 `saveCorrectedResume(resumeInfo)`。

请求：

```json
{
  "title": "Java 后端开发简历",
  "skillName": "Java, Spring Boot, MySQL, Redis",
  "personalContext": "熟悉 Java 后端开发，具备项目实践经验。",
  "status": "SAVED",
  "educations": [
    {
      "educationInfoId": 11,
      "university": "示例大学",
      "major": "软件工程",
      "degree": "本科",
      "startTime": "2022-09-01",
      "endTime": "2026-06-30"
    }
  ],
  "projects": [
    {
      "projectInfoId": 21,
      "projectName": "智能简历平台",
      "role": "后端开发",
      "introduction": "面向求职者的简历解析与优化系统",
      "content": "负责 PDF 解析、Agent 调用和 MySQL 落库接口设计。",
      "startTime": "2026-03-01",
      "endTime": "2026-06-30"
    }
  ],
  "interns": [],
  "awards": []
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "resumeId": 1001,
    "status": "SAVED"
  }
}
```

处理结果：

- 更新 `resume`。
- 更新或重建 `education_info`、`project_info`、`intern_info`、`award_info`。
- 不创建版本记录。

### DELETE /resumes/{resumeId}

软删除简历。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

## UC-04 选择模板并生成 LaTeX 简历

### GET /resume-templates

对应 SOC-08 `queryResumeTemplates()`。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "resumeTemplateId": 1,
      "templateName": "通用简洁模板",
      "latex": "templates/general.tex",
      "previewUrl": "/files/templates/general.png",
      "status": "ACTIVE"
    }
  ]
}
```

### POST /resumes/{resumeId}/generate-latex

对应 SOC-09 `generateLatexResume(resumeId, templateId)`。

请求：

```json
{
  "resumeTemplateId": 1
}
```

处理过程：

- 更新 `resume.resume_template_id`。
- 读取简历完整信息。
- 读取 `resume_template.latex` 指向的本地 LaTeX 主模板文件，例如 `Latex/1/resume/resume-zh_CN.tex`。
- 调用 `LatexTemplateAgent`，只读取主 `.tex` 模板源码并生成完整简历 `.tex`。
- 复制主模板文件所在目录的全部资源，将生成后的主 `.tex`、样式文件、字体和图片等一起打包为 zip。
- 返回 zip 下载链接。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "resumeId": 1001,
    "resumeTemplateId": 1,
    "latexFileName": "resume-zh_CN.tex",
    "zipFileName": "resume_1001.zip",
    "downloadUrl": "/api/v1/resumes/1001/latex/download",
    "warnings": []
  }
}
```

### GET /resumes/{resumeId}/latex/download

下载生成后的 LaTeX 模板 zip 包。

响应：

```http
Content-Type: application/zip
Content-Disposition: attachment; filename="resume_1001.zip"
```

## UC-05 岗位 URL 解析与匹配分析

### POST /resumes/{resumeId}/jobs/analyze

对应 SOC-10 `submitJobUrl(resumeId, jobUrl)`。

请求：

```json
{
  "jobUrl": "https://www.zhipin.com/job_detail/example.html"
}
```

处理过程：

- 保存岗位 URL。
- 抓取 Boss 直聘岗位正文。
- 保存岗位名称、公司名称和岗位内容。
- 调用 `JobAnalysisAgent`。
- Agent 分析岗位是否适合当前简历，输出匹配度、理由和置信来源。
- 将结果保存到 `job.content`。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "jobId": 501,
    "resumeId": 1001,
    "jobUrl": "https://www.zhipin.com/job_detail/example.html",
    "jobName": "Java 后端开发工程师",
    "company": "示例科技有限公司",
    "status": "PARSED",
    "matchScore": 82.5,
    "suitable": true,
    "confidenceSource": [
      "简历技能包含 Spring Boot、MySQL、Redis",
      "项目经历包含后端接口和数据库设计",
      "岗位要求包含 Java 后端开发经验"
    ],
    "analysis": "该岗位与当前简历整体匹配度较高，但项目经历中的量化结果不足。"
  }
}
```

### GET /resumes/{resumeId}/jobs

查询某份简历关联的岗位分析记录。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "jobId": 501,
      "jobName": "Java 后端开发工程师",
      "company": "示例科技有限公司",
      "status": "PARSED",
      "createdAt": "2026-07-01T10:00:00"
    }
  ]
}
```

### GET /jobs/{jobId}

查看岗位抓取与分析详情。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "jobId": 501,
    "resumeId": 1001,
    "jobUrl": "https://www.zhipin.com/job_detail/example.html",
    "jobName": "Java 后端开发工程师",
    "company": "示例科技有限公司",
    "content": "岗位正文、岗位要求、匹配分析、置信来源等内容",
    "status": "PARSED"
  }
}
```

## UC-06 简历优化建议

### POST /resumes/{resumeId}/optimize

对应 SOC-11 `requestResumeOptimization(resumeId, jobId)`。

请求：

```json
{
  "jobId": 501
}
```

说明：

- `jobId` 可选。
- 不传 `jobId` 时，只分析简历自身内容是否合理。
- 传 `jobId` 时，结合岗位内容分析技能匹配和表达重点。

处理过程：

- 读取 `resume` 和经历明细表。
- 可选读取 `job.content`。
- 调用 `ResumeOptimizeAgent`。
- 检查技能是否足够、个人介绍是否合理、项目/实习经历是否使用 STAR/STAT 表达法则。
- 优化建议不能虚构经历、成果、数字或项目。
- 保存到 `opt`。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "optId": 9001,
    "resumeId": 1001,
    "jobId": 501,
    "score": 82.5,
    "status": "NEW",
    "content": "简历技能与岗位基本匹配。项目经历描述了工作内容，但缺少任务背景、行动过程和结果说明，建议按 STAR/STAT 法则补充；不得编造不存在的数据。"
  }
}
```

### GET /resumes/{resumeId}/opts

查询某份简历的优化建议记录。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "optId": 9001,
      "jobId": 501,
      "score": 82.5,
      "status": "NEW",
      "createdAt": "2026-07-01T10:00:00"
    }
  ]
}
```

### PATCH /opts/{optId}/status

对应 SOC-12 `markOptimizationUsed(optId)`。

请求：

```json
{
  "status": "USED"
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

## UC-07 管理用户账号

### GET /admin/users

对应 SOC-13 `selectUserManagement()` 和 SOC-14 `searchUser(queryCondition)`。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `keyword` | `string` | 否 | 按账号或邮箱搜索 |
| `status` | `string` | 否 | 用户状态 |
| `page` | `int` | 否 | 页码 |
| `pageSize` | `int` | 否 | 每页数量 |

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "userId": 1,
        "account": "zhangsan",
        "email": "zhangsan@example.com",
        "status": "ACTIVE",
        "registerTime": "2026-07-01T09:00:00"
      }
    ],
    "page": 1,
    "pageSize": 10,
    "total": 1
  }
}
```

### PATCH /admin/users/{userId}/disable

对应 SOC-15 `disableUser(userId)`。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "userId": 1,
    "status": "DISABLED"
  }
}
```

### PATCH /admin/users/{userId}/enable

对应 SOC-16 `enableUser(userId)`。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "userId": 1,
    "status": "ACTIVE"
  }
}
```

## 接口到 SOC 映射

| SOC | 系统操作 | API |
|---|---|---|
| SOC-01 | `requestRegister()` | 前端页面操作 |
| SOC-02 | `submitRegisterInfo(account, password, email)` | `POST /auth/register` |
| SOC-03 | `submitLoginInfo(account, password)` | `POST /auth/login` |
| SOC-04 | `chooseUploadPDFResume()` | 前端页面操作 |
| SOC-05 | `uploadPDFResume(pdfFile)` | `POST /resumes/upload-pdf` |
| SOC-06 | `selectResumeForCheck(resumeId)` | `GET /resumes/{resumeId}` |
| SOC-07 | `saveCorrectedResume(resumeInfo)` | `PUT /resumes/{resumeId}` |
| SOC-08 | `queryResumeTemplates()` | `GET /resume-templates` |
| SOC-09 | `generateLatexResume(resumeId, templateId)` | `POST /resumes/{resumeId}/generate-latex` |
| SOC-10 | `submitJobUrl(resumeId, jobUrl)` | `POST /resumes/{resumeId}/jobs/analyze` |
| SOC-11 | `requestResumeOptimization(resumeId, jobId)` | `POST /resumes/{resumeId}/optimize` |
| SOC-12 | `markOptimizationUsed(optId)` | `PATCH /opts/{optId}/status` |
| SOC-13 | `selectUserManagement()` | `GET /admin/users` |
| SOC-14 | `searchUser(queryCondition)` | `GET /admin/users?keyword=...` |
| SOC-15 | `disableUser(userId)` | `PATCH /admin/users/{userId}/disable` |
| SOC-16 | `enableUser(userId)` | `PATCH /admin/users/{userId}/enable` |

## 第一版开发建议

第一版建议优先实现以下接口，保证核心演示闭环：

1. `POST /auth/register`
2. `POST /auth/login`
3. `POST /resumes/upload-pdf`
4. `GET /resumes/{resumeId}`
5. `PUT /resumes/{resumeId}`
6. `GET /resume-templates`
7. `POST /resumes/{resumeId}/generate-latex`
8. `POST /resumes/{resumeId}/jobs/analyze`
9. `POST /resumes/{resumeId}/optimize`
10. `GET /admin/users`
11. `PATCH /admin/users/{userId}/disable`
