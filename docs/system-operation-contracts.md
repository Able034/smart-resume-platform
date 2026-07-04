# System Operation Contracts

本文档定义系统顺序图中出现的系统操作契约。当前版本以精简数据库设计为准，只描述第一版核心闭环需要的持久化对象。

## UC-01 用户注册与登录

### SOC-01 requestRegister()

**Operation:** `requestRegister()`

**Cross References:** UC-01 用户注册与登录；领域模型类 `UserAccount`。

**Preconditions:**

- 系统正常运行。
- 访客尚未提交注册信息。

**Postconditions:**

- 系统展示注册表单。
- 没有创建新的 `UserAccount`。

### SOC-02 submitRegisterInfo(account, password, email)

**Operation:** `submitRegisterInfo(account, password, email)`

**Cross References:** UC-01 用户注册与登录；领域模型类 `UserAccount`。

**Preconditions:**

- 注册表单已展示。
- 账号、密码、邮箱均已填写并通过基本格式校验。
- 系统中不存在相同 `account` 或 `email` 的有效用户。

**Postconditions:**

- 创建新的 `UserAccount`。
- 密码以 `password_hash` 形式保存。
- 用户状态设置为 `ACTIVE`。
- 返回注册成功结果。

### SOC-03 submitLoginInfo(account, password)

**Operation:** `submitLoginInfo(account, password)`

**Cross References:** UC-01 用户注册与登录；领域模型类 `UserAccount`。

**Preconditions:**

- 登录表单已展示。
- 用户提交了账号和密码。
- 系统中存在匹配的有效用户账号。

**Postconditions:**

- 系统校验密码。
- 更新 `last_login_time`。
- 返回登录凭证和当前用户信息。

## UC-02 PDF 简历解析入库

### SOC-04 chooseUploadPDFResume()

**Operation:** `chooseUploadPDFResume()`

**Cross References:** UC-02 PDF 简历解析入库；领域模型类 `Resume`、`ResumeParseAgent`。

**Preconditions:**

- 用户已登录。
- 用户账号状态为 `ACTIVE`。

**Postconditions:**

- 系统展示 PDF 上传入口。
- 没有创建简历数据。

### SOC-05 uploadPDFResume(pdfFile)

**Operation:** `uploadPDFResume(pdfFile)`

**Cross References:** UC-02 PDF 简历解析入库；领域模型类 `PdfText`、`ResumeParseAgent`、`StandardResume`、`Resume`、`EducationInfo`、`ProjectInfo`、`InternInfo`、`AwardInfo`。

**Preconditions:**

- 用户已登录。
- 用户选择了本地 PDF 文件。
- 文件格式为 PDF，大小满足系统限制。

**Postconditions:**

- 系统校验 PDF 文件格式和大小。
- 系统将 PDF 内容抽取为字符串文本。
- `ResumeParseAgent` 根据字符串文本解析出标准简历对象。
- 标准简历对象通过 Pydantic 校验。
- 系统创建 `resume` 记录。
- 系统按解析结果创建 `education_info`、`project_info`、`intern_info`、`award_info` 明细记录。
- 简历状态设置为 `DRAFT` 或 `SAVED`。
- 系统返回 `resumeId` 和解析结果预览，供用户校对。

## UC-03 用户校对与编辑简历

### SOC-06 selectResumeForCheck(resumeId)

**Operation:** `selectResumeForCheck(resumeId)`

**Cross References:** UC-03 用户校对与编辑简历；领域模型类 `Resume`、`EducationInfo`、`ProjectInfo`、`InternInfo`、`AwardInfo`。

**Preconditions:**

- 用户已登录。
- 目标简历存在。
- 目标简历属于当前登录用户。

**Postconditions:**

- 系统读取 `resume` 主表信息。
- 系统读取该简历关联的教育背景、项目经历、实习经历和获奖经历。
- 系统展示可校对和编辑的简历详情。

### SOC-07 saveCorrectedResume(resumeInfo)

**Operation:** `saveCorrectedResume(resumeInfo)`

**Cross References:** UC-03 用户校对与编辑简历；领域模型类 `Resume`、`EducationInfo`、`ProjectInfo`、`InternInfo`、`AwardInfo`。

**Preconditions:**

- 用户已登录。
- 目标简历属于当前登录用户。
- 用户提交了校对后的简历信息。
- 必填字段和字段格式满足系统规则。

**Postconditions:**

- 系统更新 `resume` 主表信息。
- 系统更新对应的 `education_info`、`project_info`、`intern_info`、`award_info` 记录。
- 简历状态更新为 `SAVED`。
- `updated_at` 被刷新。
- 返回保存成功结果。

## UC-04 选择模板并生成 LaTeX 简历

### SOC-08 queryResumeTemplates()

**Operation:** `queryResumeTemplates()`

**Cross References:** UC-04 选择模板并生成 LaTeX 简历；领域模型类 `ResumeTemplate`。

**Preconditions:**

- 用户已登录。

**Postconditions:**

- 系统查询状态为 `ACTIVE` 的 `resume_template` 记录。
- 返回模板名称、预览图和模板 ID。

### SOC-09 generateLatexResume(resumeId, templateId)

**Operation:** `generateLatexResume(resumeId, templateId)`

**Cross References:** UC-04 选择模板并生成 LaTeX 简历；领域模型类 `Resume`、`ResumeTemplate`、`LatexTemplateAgent`。

**Preconditions:**

- 用户已登录。
- 目标简历存在且属于当前用户。
- 目标模板存在且状态为 `ACTIVE`。
- 简历信息已经校对并保存。

**Postconditions:**

- 系统更新 `resume.resume_template_id`。
- 系统读取简历主表和关联经历明细。
- 系统读取 `resume_template.latex` 指向的 LaTeX 模板文件。
- `LatexTemplateAgent` 根据简历信息和模板文件生成最终 LaTeX 代码。
- 系统生成 LaTeX 代码下载链接。
- 返回下载链接和必要的生成提示。

## UC-05 岗位 URL 解析与匹配分析

### SOC-10 submitJobUrl(resumeId, jobUrl)

**Operation:** `submitJobUrl(resumeId, jobUrl)`

**Cross References:** UC-05 岗位 URL 解析与匹配分析；领域模型类 `Resume`、`Job`、`JobCrawler`、`JobAnalysisAgent`。

**Preconditions:**

- 用户已登录。
- 目标简历存在且属于当前用户。
- 用户输入 Boss 直聘等招聘网站岗位 URL。

**Postconditions:**

- 系统创建或更新 `job` 记录，保存 `resume_id` 和 `job_url`。
- `JobCrawler` 抓取岗位页面正文。
- 系统把岗位正文、岗位名称、公司名称等内容写入 `job.content`、`job.job_name`、`job.company`。
- `JobAnalysisAgent` 读取简历信息和岗位正文。
- Agent 输出岗位是否合适、匹配度、置信来源等分析结果。
- 系统将分析结果合并保存到 `job.content`。
- `job.status` 更新为 `PARSED`；失败时更新为 `FAILED` 并返回错误原因。

## UC-06 简历优化建议

### SOC-11 requestResumeOptimization(resumeId, jobId)

**Operation:** `requestResumeOptimization(resumeId, jobId)`

**Cross References:** UC-06 简历优化建议；领域模型类 `Resume`、`Job`、`Opt`、`ResumeOptimizeAgent`。

**Preconditions:**

- 用户已登录。
- 目标简历存在且属于当前用户。
- 如果传入 `jobId`，目标岗位记录存在且关联当前简历。
- 简历已有可分析内容。

**Postconditions:**

- 系统读取简历主表、教育背景、项目经历、实习经历、获奖经历。
- 如果存在岗位上下文，系统读取 `job.content`。
- `ResumeOptimizeAgent` 分析简历内容是否合理、技能是否足够、项目/实习经历是否使用 STAR/STAT 表达法则。
- Agent 只能基于已有简历内容提出建议，不虚构项目、经历、数据或成果。
- 系统创建 `opt` 记录，保存优化建议内容、评分和关联岗位 ID。
- 返回优化建议和评分。

### SOC-12 markOptimizationUsed(optId)

**Operation:** `markOptimizationUsed(optId)`

**Cross References:** UC-06 简历优化建议；领域模型类 `Opt`。

**Preconditions:**

- 用户已登录。
- 目标优化记录存在。
- 目标优化记录关联的简历属于当前用户。

**Postconditions:**

- `opt.status` 更新为 `USED`。
- 返回更新成功结果。

## UC-07 管理用户账号

### SOC-13 selectUserManagement()

**Operation:** `selectUserManagement()`

**Cross References:** UC-07 管理用户账号；领域模型类 `Admin`、`UserAccount`。

**Preconditions:**

- 管理员已登录。
- 管理员账号状态为 `ACTIVE`。
- 当前账号角色为 `ADMIN`。

**Postconditions:**

- 系统展示用户管理页面。
- 系统读取 `user_account` 列表。

### SOC-14 searchUser(queryCondition)

**Operation:** `searchUser(queryCondition)`

**Cross References:** UC-07 管理用户账号；领域模型类 `Admin`、`UserAccount`。

**Preconditions:**

- 管理员已登录。
- 用户管理页面已打开。

**Postconditions:**

- 系统按账号、邮箱或状态查询 `user_account`。
- 返回符合条件的用户列表。

### SOC-15 disableUser(userId)

**Operation:** `disableUser(userId)`

**Cross References:** UC-07 管理用户账号；领域模型类 `Admin`、`UserAccount`。

**Preconditions:**

- 管理员已登录。
- 目标用户存在。
- 目标用户状态不是 `DISABLED`。

**Postconditions:**

- 系统将目标 `UserAccount.status` 更新为 `DISABLED`。
- 被禁用用户无法继续登录。
- 返回禁用成功结果。

### SOC-16 enableUser(userId)

**Operation:** `enableUser(userId)`

**Cross References:** UC-07 管理用户账号；领域模型类 `Admin`、`UserAccount`。

**Preconditions:**

- 管理员已登录。
- 目标用户存在。
- 目标用户状态为 `DISABLED`。

**Postconditions:**

- 系统将目标 `UserAccount.status` 更新为 `ACTIVE`。
- 返回启用成功结果。
