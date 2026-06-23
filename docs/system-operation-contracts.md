# System Operation Contracts

This document defines the system operation contracts for all system operations shown in the System Sequence Diagrams.

## UC-01 User Registration and Login

### SOC-01 requestRegister()

**Operation:** `requestRegister()`

**Cross References:** Use Case UC-01 User Registration and Login; SSD UC-01; Domain Model classes `UserAccount`, `LoginSession`.

**Preconditions:**
- The system is running and available.
- The visitor has not yet started the registration form flow.

**Postconditions:**
- The registration form was displayed.
- No `UserAccount` object was created.
- No persistent system data was changed.

### SOC-02 submitRegisterInfo(account, password, email)

**Operation:** `submitRegisterInfo(account, password, email)`

**Cross References:** Use Case UC-01 User Registration and Login; SSD UC-01; Domain Model class `UserAccount`.

**Preconditions:**
- The registration form is displayed.
- The submitted account, password, and email are present and syntactically valid.
- No active `UserAccount` with the same account already exists.

**Postconditions:**
- The submitted registration data was validated.
- A new `UserAccount` was created.
- The password was stored in a protected form.
- The `UserAccount` status was set to active.
- A registration success result was returned.

### SOC-03 submitLoginInfo(account, password)

**Operation:** `submitLoginInfo(account, password)`

**Cross References:** Use Case UC-01 User Registration and Login; SSD UC-01; Domain Model classes `UserAccount`, `LoginSession`.

**Preconditions:**
- The login form is available.
- The submitted account and password are present.
- A matching active `UserAccount` exists.

**Postconditions:**
- The submitted credentials were verified.
- A new `LoginSession` was created.
- The `LoginSession` was associated with the authenticated `UserAccount`.
- The session expiration time was set.
- A login success result was returned.

## UC-02 Create Resume

### SOC-04 chooseCreateResume()

**Operation:** `chooseCreateResume()`

**Cross References:** Use Case UC-02 Create Resume; SSD UC-02; Domain Model classes `UserAccount`, `Resume`, `ResumeSection`, `ResumeVersion`.

**Preconditions:**
- The user is logged in.
- The user's `UserAccount` is active.

**Postconditions:**
- The resume input form was displayed.
- No `Resume` object was created.
- No persistent resume data was changed.

### SOC-05 fillResumeInfo(info)

**Operation:** `fillResumeInfo(info)`

**Cross References:** Use Case UC-02 Create Resume; SSD UC-02; Domain Model classes `Resume`, `ResumeSection`.

**Preconditions:**
- The user is logged in.
- The resume input form is displayed.
- The resume information is provided by the user.

**Postconditions:**
- The entered resume information was accepted by the system.
- The entered content was organized as draft resume section data.
- No final `Resume` record was created.

### SOC-06 saveResume()

**Operation:** `saveResume()`

**Cross References:** Use Case UC-02 Create Resume; SSD UC-02; Domain Model classes `UserAccount`, `Resume`, `ResumeSection`, `ResumeVersion`.

**Preconditions:**
- The user is logged in.
- Draft resume information exists.
- Required fields and format rules are satisfied.

**Postconditions:**
- A new `Resume` was created.
- The `Resume` was associated with the logged-in `UserAccount`.
- One or more `ResumeSection` records were created.
- An initial `ResumeVersion` was created.
- The `Resume` status was set to saved.
- The new `resumeId` was returned.

## UC-03 Convert PDF Resume to Online Resume

### SOC-07 uploadPDFResume(pdfFile)

**Operation:** `uploadPDFResume(pdfFile)`

**Cross References:** Use Case UC-03 Convert PDF Resume to Online Resume; SSD UC-03; Domain Model classes `UserAccount`, `PdfFile`, `Resume`, `ResumeSection`.

**Preconditions:**
- The user is logged in.
- A local PDF resume file is selected.
- The selected file satisfies the configured upload size limit.

**Postconditions:**
- The uploaded file was validated as a PDF file.
- A `PdfFile` record was stored.
- The `PdfFile` was associated with the logged-in `UserAccount`.
- Resume information was parsed from the PDF content.
- A parsed resume preview was generated and displayed.

### SOC-08 confirmParsedResume()

**Operation:** `confirmParsedResume()`

**Cross References:** Use Case UC-03 Convert PDF Resume to Online Resume; SSD UC-03; Domain Model classes `PdfFile`, `ResumeSection`.

**Preconditions:**
- A parsed resume preview is available.
- The user has reviewed the parsed resume information.

**Postconditions:**
- The parsed resume information was confirmed by the user.
- The parsed section data was marked as ready for saving.
- No final online `Resume` was created yet.

### SOC-09 saveOnlineResume()

**Operation:** `saveOnlineResume()`

**Cross References:** Use Case UC-03 Convert PDF Resume to Online Resume; SSD UC-03; Domain Model classes `UserAccount`, `PdfFile`, `Resume`, `ResumeSection`.

**Preconditions:**
- The user is logged in.
- Confirmed parsed resume information exists.
- Required resume fields are complete enough to be saved.

**Postconditions:**
- A new online `Resume` was created from the parsed PDF data.
- The `Resume` was associated with the logged-in `UserAccount`.
- The `Resume` was associated with the uploaded `PdfFile`.
- One or more `ResumeSection` records were created from the parsed content.
- The online resume was saved.
- The new `resumeId` was returned.

## UC-04 Edit Resume

### SOC-10 selectResumeForEditing(resumeId)

**Operation:** `selectResumeForEditing(resumeId)`

**Cross References:** Use Case UC-04 Edit Resume; SSD UC-04; Domain Model classes `UserAccount`, `Resume`, `ResumeSection`, `ResumeVersion`.

**Preconditions:**
- The user is logged in.
- The target `Resume` exists.
- The target `Resume` belongs to the logged-in `UserAccount`.

**Postconditions:**
- The current `Resume` content was loaded.
- The related `ResumeSection` records were retrieved.
- The resume editing view was displayed.
- No resume data was changed.

### SOC-11 modifyResumeContent(resumeInfo)

**Operation:** `modifyResumeContent(resumeInfo)`

**Cross References:** Use Case UC-04 Edit Resume; SSD UC-04; Domain Model classes `Resume`, `ResumeSection`.

**Preconditions:**
- The user is logged in.
- The target `Resume` is loaded for editing.
- The edited resume information is provided.

**Postconditions:**
- The edited resume information was accepted by the system.
- The changed section data was recorded as an edit draft.
- No new `ResumeVersion` was created yet.

### SOC-12 saveEditedResume()

**Operation:** `saveEditedResume()`

**Cross References:** Use Case UC-04 Edit Resume; SSD UC-04; Domain Model classes `Resume`, `ResumeSection`, `ResumeVersion`.

**Preconditions:**
- The user is logged in.
- An edit draft exists for the target `Resume`.
- The edited content satisfies the resume validation rules.

**Postconditions:**
- The target `Resume` was updated.
- The affected `ResumeSection` records were updated.
- A new `ResumeVersion` was created.
- The resume update time was refreshed.
- The new `versionId` was returned.

## UC-05 Resume Optimization

### SOC-13 selectResumeForDiagnosis(resumeId)

**Operation:** `selectResumeForDiagnosis(resumeId)`

**Cross References:** Use Case UC-05 Resume Optimization; SSD UC-05; Domain Model classes `UserAccount`, `Resume`, `ResumeSection`, `OptimizationTask`.

**Preconditions:**
- The user is logged in.
- The target `Resume` exists.
- The target `Resume` belongs to the logged-in `UserAccount`.

**Postconditions:**
- The selected `Resume` was loaded for diagnosis.
- The related `ResumeSection` records were collected.
- The diagnosis context was prepared.
- No diagnosis report was generated yet.

### SOC-14 submitJobUrl()

**Operation:** `submitJobUrl()`

**Cross References:** Use Case UC-05 Resume Optimization; SSD UC-05; Domain Model classes `JobUrl`, `JobDescription`, `JobRequirement`, `OptimizationTask`, `DiagnosisReport`, `OptimizationSuggestion`.

**Preconditions:**
- A resume has been selected for diagnosis.
- A target job URL is provided by the user.
- Optimization rules and job analysis services are available.

**Postconditions:**
- A `JobUrl` was recorded.
- A `JobDescription` was fetched and summarized from the target job URL.
- One or more `JobRequirement` records were extracted.
- An `OptimizationTask` was created.
- The selected resume content was analyzed against the extracted job requirements.
- A diagnosis report draft was generated.
- One or more `OptimizationSuggestion` records were generated.
- The optimization report and suggestions were displayed.

### SOC-15 saveOptimizationReport(reportId)

**Operation:** `saveOptimizationReport(reportId)`

**Cross References:** Use Case UC-05 Resume Optimization; SSD UC-05; Domain Model classes `OptimizationTask`, `DiagnosisReport`, `OptimizationSuggestion`.

**Preconditions:**
- The user is logged in.
- A generated diagnosis report is available.
- The report belongs to the selected resume and the logged-in user.

**Postconditions:**
- The `DiagnosisReport` was saved.
- The `DiagnosisReport` was linked to the corresponding `OptimizationTask`.
- The `DiagnosisReport` was linked to the selected `Resume`.
- The related `OptimizationSuggestion` records were saved.
- The saved `reportId` was returned.

## UC-06 Export Resume

### SOC-16 selectResumeForExport(resumeId)

**Operation:** `selectResumeForExport(resumeId)`

**Cross References:** Use Case UC-06 Export Resume; SSD UC-06; Domain Model classes `UserAccount`, `Resume`, `ResumeSection`, `ResumeTemplate`, `ExportFile`.

**Preconditions:**
- The user is logged in.
- The target `Resume` exists.
- The target `Resume` belongs to the logged-in `UserAccount`.
- The resume content is complete enough to be exported.
- A usable `ResumeTemplate` is available.

**Postconditions:**
- The selected `Resume` was checked for exportability.
- The related `ResumeSection` data was assembled.
- The available export format options were displayed.
- The selected or default `ResumeTemplate` was applied.
- An `ExportFile` was generated.
- A download URL was created.
- The exported resume file link was returned.

## UC-07 Resume Version Management

### SOC-17 selectResumeVersionManagement(resumeId)

**Operation:** `selectResumeVersionManagement(resumeId)`

**Cross References:** Use Case UC-07 Resume Version Management; SSD UC-07; Domain Model classes `UserAccount`, `Resume`, `ResumeVersion`, `VersionSection`.

**Preconditions:**
- The user is logged in.
- The target `Resume` exists.
- The target `Resume` belongs to the logged-in `UserAccount`.
- At least one `ResumeVersion` exists for the target `Resume`.

**Postconditions:**
- The target `Resume` was loaded.
- The related `ResumeVersion` list was retrieved.
- Version summary data was displayed.
- No current resume content was changed.

### SOC-18 selectHistoryVersion(versionId)

**Operation:** `selectHistoryVersion(versionId)`

**Cross References:** Use Case UC-07 Resume Version Management; SSD UC-07; Domain Model classes `ResumeVersion`, `VersionSection`.

**Preconditions:**
- The resume version management view is displayed.
- The selected `ResumeVersion` exists.
- The selected `ResumeVersion` belongs to the current `Resume`.

**Postconditions:**
- The selected `ResumeVersion` was loaded.
- The related `VersionSection` records were retrieved.
- The historical version content was displayed.
- No current resume content was changed.

## UC-08 Manage User Accounts

### SOC-19 selectUserManagement()

**Operation:** `selectUserManagement()`

**Cross References:** Use Case UC-08 Manage User Accounts; SSD UC-08; Domain Model classes `Admin`, `UserAccount`.

**Preconditions:**
- The administrator is logged in.
- The administrator account is active.
- The administrator has user management permission.

**Postconditions:**
- The user management view was displayed.
- The `UserAccount` list was retrieved.
- No user account status was changed.

### SOC-20 searchUser(queryCondition)

**Operation:** `searchUser(queryCondition)`

**Cross References:** Use Case UC-08 Manage User Accounts; SSD UC-08; Domain Model classes `Admin`, `UserAccount`.

**Preconditions:**
- The administrator is logged in.
- The user management view is displayed.
- A query condition is provided or the default query condition is available.

**Postconditions:**
- Matching `UserAccount` records were retrieved.
- The user search result was displayed.
- No user account data was changed.

### SOC-21 disableUser(userId)

**Operation:** `disableUser(userId)`

**Cross References:** Use Case UC-08 Manage User Accounts; SSD UC-08; Domain Model classes `Admin`, `UserAccount`.

**Preconditions:**
- The administrator is logged in.
- The administrator has user disable permission.
- The target `UserAccount` exists.
- The target `UserAccount` is not already disabled.

**Postconditions:**
- The target `UserAccount` was selected for disabling.
- A disable confirmation request was displayed.
- No user account status was changed yet.

### SOC-22 confirmDisable()

**Operation:** `confirmDisable()`

**Cross References:** Use Case UC-08 Manage User Accounts; SSD UC-08; Domain Model classes `Admin`, `UserAccount`.

**Preconditions:**
- The administrator is logged in.
- A disable confirmation request is displayed.
- A target `UserAccount` has been selected for disabling.

**Postconditions:**
- The target `UserAccount` status was changed to disabled.
- The account status change was persisted.
- Future login by the disabled `UserAccount` was prevented.
- A disable success result was displayed.

## UC-09 View System Logs

### SOC-23 selectSystemLog()

**Operation:** `selectSystemLog()`

**Cross References:** Use Case UC-09 View System Logs; SSD UC-09; Domain Model classes `Admin`, `SystemLog`.

**Preconditions:**
- The administrator is logged in.
- The administrator account is active.
- The administrator has log viewing permission.

**Postconditions:**
- The system log view was displayed.
- The `SystemLog` list was retrieved.
- System log summary records were displayed.
- No persistent log data was changed.

### SOC-24 filterLogs(filterCondition)

**Operation:** `filterLogs(filterCondition)`

**Cross References:** Use Case UC-09 View System Logs; SSD UC-09; Domain Model classes `Admin`, `SystemLog`.

**Preconditions:**
- The administrator is logged in.
- The system log view is displayed.
- A filter condition is provided.

**Postconditions:**
- Matching `SystemLog` records were retrieved.
- The filtered log list was displayed.
- No persistent log data was changed.

### SOC-25 selectLogDetail(logId)

**Operation:** `selectLogDetail(logId)`

**Cross References:** Use Case UC-09 View System Logs; SSD UC-09; Domain Model classes `Admin`, `SystemLog`.

**Preconditions:**
- The administrator is logged in.
- The selected `SystemLog` exists.
- The administrator has permission to view the selected log detail.

**Postconditions:**
- The selected `SystemLog` detail was retrieved.
- The log detail was displayed.
- No persistent log data was changed.
