import { XMLParser, XMLBuilder } from 'fast-xml-parser'

const parser = new XMLParser({ ignoreAttributes: false })
const builder = new XMLBuilder({ ignoreAttributes: false, format: true })

// Toggle mock mode: set VITE_USE_MOCK=true to use in-browser mock; default false to call backend/mock server
const MOCK = import.meta.env.VITE_USE_MOCK ? import.meta.env.VITE_USE_MOCK === 'true' : false
const BACKEND_MAP: Record<string, string> = {
    A: import.meta.env.VITE_API_URL_A || '',
    B: import.meta.env.VITE_API_URL_B || '',
    C: import.meta.env.VITE_API_URL_C || '',
    INTEGRATION: import.meta.env.VITE_API_URL_INTEGRATION || ''
}
const INTEGRATION_API_KEY = import.meta.env.VITE_INTEGRATION_API_KEY || 'integration-server-api-key-2026'

type Course = { id: string; name: string; time: number; score: number; teacher: string; location: string; collegeId?: string }
type Enrollment = { enrollmentId: string; cid: string; name: string; status: 'ENROLLED' | 'WITHDRAWN'; sid: string }
type CollegeSummary = { collegeId: string; studentCount: number; courseCount: number; enrollmentCount: number }
type StatsSummary = {
    colleges: CollegeSummary[]
    totals: { students: number; courses: number; enrollments: number }
    categories?: { category: string; enrollmentCount: number; percentage: number }[]
}
type LoginResult = { code: number; message: string; data: { sid: string; name: string } }

const MOCK_ENROLLMENTS_KEY = 'eduintegrate.mock.enrollments'

const localMockCourses: Course[] = [
    { id: 'A001', name: '数据库系统', time: 32, score: 3, teacher: '张老师', location: '1-301', collegeId: 'A' },
    { id: 'A003', name: '数仓基础', time: 24, score: 2, teacher: '王老师', location: '3-105', collegeId: 'A' },
    { id: 'B001', name: '分布式系统', time: 32, score: 3, teacher: '周老师', location: 'B-201', collegeId: 'B' },
    { id: 'B002', name: '机器学习基础', time: 24, score: 2, teacher: '吴老师', location: 'B-305', collegeId: 'B' },
    { id: 'C001', name: '软件工程', time: 32, score: 3, teacher: '陈老师', location: 'C-401', collegeId: 'C' },
    { id: 'C003', name: '数据挖掘', time: 32, score: 3, teacher: '黄老师', location: 'C-210', collegeId: 'C' }
]

// 本院课程（仅属于当前学院，不带 collegeId 或 collegeId 等于当前学院）
const localMockLocalCourses: Course[] = [
    { id: 'L001', name: '高等数学', time: 48, score: 4, teacher: '赵老师', location: '1-101' },
    { id: 'L002', name: '线性代数', time: 32, score: 3, teacher: '孙老师', location: '1-102' },
    { id: 'L003', name: '概率论', time: 32, score: 3, teacher: '周老师', location: '1-103' },
    { id: 'L004', name: '大学物理', time: 48, score: 4, teacher: '吴老师', location: '2-101' },
    { id: 'L005', name: '计算机导论', time: 24, score: 2, teacher: '郑老师', location: '2-102' }
]

const localMockState = {
    users: {
        S2024001: { name: '张三', password: '123456' },
        S2024002: { name: '李四', password: '123456' },
        S2024003: { name: '王五', password: '123456' }
    },
    byCollege: [
        { collegeId: 'A', studentCount: 50, courseCount: 10, enrollmentCount: 80 },
        { collegeId: 'B', studentCount: 50, courseCount: 10, enrollmentCount: 90 },
        { collegeId: 'C', studentCount: 50, courseCount: 10, enrollmentCount: 100 }
    ],
    enrollments: [
        { enrollmentId: 'E1', cid: 'C001', sid: 'S2024001', status: 'ENROLLED', name: '数据库系统' }
    ] as Enrollment[]
}

function loadMockEnrollments() {
    try {
        const raw = localStorage.getItem(MOCK_ENROLLMENTS_KEY)
        if (!raw) return
        const data = JSON.parse(raw)
        if (Array.isArray(data)) {
            localMockState.enrollments = data
        }
    } catch {
        localStorage.removeItem(MOCK_ENROLLMENTS_KEY)
    }
}

function saveMockEnrollments() {
    localStorage.setItem(MOCK_ENROLLMENTS_KEY, JSON.stringify(localMockState.enrollments))
}

function localMockSharedCourses() {
    return { classes: localMockCourses.map(normalizeCourse) }
}

function localMockLocalCoursesFiltered(collegeId: string) {
    return { classes: localMockLocalCourses.map(normalizeCourse) }
}

function localMockStats() {
    loadMockEnrollments()
    const enrollments = localMockState.enrollments.filter(e => e.status === 'ENROLLED').length
    const colleges = localMockState.byCollege.map(item => ({
        collegeId: item.collegeId,
        studentCount: item.studentCount,
        courseCount: item.courseCount,
        enrollmentCount: item.enrollmentCount
    }))
    const totals = colleges.reduce(
        (acc, item) => ({
            students: acc.students + item.studentCount,
            courses: acc.courses + item.courseCount,
            enrollments: acc.enrollments + item.enrollmentCount
        }),
        { students: 0, courses: 0, enrollments: 0 }
    )
    if (totals.enrollments === 0) {
        totals.enrollments = enrollments
    }
    return {
        colleges,
        totals,
        categories: [
            { category: '数据与数据库', enrollmentCount: 96, percentage: 36 },
            { category: 'XML 与系统集成', enrollmentCount: 72, percentage: 27 },
            { category: '工程基础', enrollmentCount: 54, percentage: 20 },
            { category: '通识拓展', enrollmentCount: 45, percentage: 17 }
        ]
    } satisfies StatsSummary
}

function localMockEnrollments(sid: string) {
    loadMockEnrollments()
    return localMockState.enrollments
        .filter(e => e.sid === sid)
        .map(e => ({
            enrollmentId: e.enrollmentId,
            cid: e.cid,
            name: e.name || getCourseName(e.cid),
            status: e.status,
            sid: e.sid
        }))
}

function normalizeArray<T>(value: T | T[] | undefined | null): T[] {
    if (!value) return []
    return Array.isArray(value) ? value : [value]
}

function parseCode(value: unknown): number {
    const n = Number(value)
    return Number.isFinite(n) ? n : 0
}

function getCourseName(cid: string) {
    return [...localMockCourses, ...localMockLocalCourses].find(c => c.id === cid)?.name || ''
}

function normalizeCourse(item: any): Course {
    return {
        id: String(item?.id ?? item?.courseId ?? item?.课程编号 ?? item?.编号 ?? item?.Cno ?? ''),
        name: String(item?.name ?? item?.courseName ?? item?.课程名称 ?? item?.名称 ?? item?.Cnm ?? ''),
        time: Number(item?.time ?? item?.hours ?? item?.课时 ?? item?.Ctm ?? 0),
        score: Number(item?.score ?? item?.credit ?? item?.credits ?? item?.学分 ?? item?.Cpt ?? 0),
        teacher: String(item?.teacher ?? item?.教师 ?? item?.老师 ?? item?.Tec ?? ''),
        location: String(item?.location ?? item?.place ?? item?.地点 ?? item?.Pla ?? ''),
        collegeId: item?.collegeId ?? item?.collegeID ?? item?.college ?? item?.学院
    }
}

function ensureXmlResponseShape(json: any) {
    const response = json?.Response || json?.response || json
    const data = response?.data || {}
    return {
        code: parseCode(response?.code),
        message: response?.message || 'success',
        data
    }
}

export async function loginWithPassword(sid: string, password: string, collegeId = 'A'): Promise<LoginResult> {
    if (MOCK) {
        const user = localMockState.users[sid as keyof typeof localMockState.users]
        if (!user || user.password !== password) {
            return { code: 401, message: 'invalid credentials', data: { sid: '', name: '' } }
        }
        return { code: 0, message: 'success', data: { sid, name: user.name } }
    }
    const xml = builder.build({ LoginRequest: { username: sid, password } })
    try {
        const json = await fetchCollegeXml(collegeId, '/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/xml', Accept: 'application/xml' },
            body: xml
        })
        const resp = ensureXmlResponseShape(json)
        const user = resp.data?.user || {}
        return {
            code: resp.code,
            message: resp.message,
            data: {
                sid: user?.studentId || resp.data?.sid || resp.data?.id || sid,
                name: user?.name || resp.data?.name || user?.username || ''
            }
        }
    } catch {
        return { code: 500, message: 'login failed', data: { sid: '', name: '' } }
    }
}

// All integration-server-facing paths (no college prefix)
const INTEGRATION_PATTERNS = [
    '/api/v1/shared-courses',
    '/api/v1/enrollments',
    '/api/v1/stats/summary',
]
// Paths with /college/{collegeId} prefix that map to college backends
const COLLEGE_PATTERNS = [
    '/api/v1/college/',
    '/api/v1/students/',
]

function resolveBaseUrl(pathname: string) {
    // Integration server paths
    if (INTEGRATION_PATTERNS.some(p => pathname.startsWith(p))) {
        return BACKEND_MAP.INTEGRATION || ''
    }
    // College-specific paths
    if (COLLEGE_PATTERNS.some(p => pathname.startsWith(p))) {
        const match = pathname.match(/\/college\/([A-C])/i)
        if (match) {
            return BACKEND_MAP[match[1].toUpperCase()] || ''
        }
    }
    // Withdraw: /api/v1/enrollments/{id}/withdraw
    if (pathname.startsWith('/api/v1/enrollments/') && pathname.endsWith('/withdraw')) {
        return BACKEND_MAP.INTEGRATION || ''
    }
    // Student enrollments: /api/v1/students/{sid}/enrollments
    if (pathname.match(/^\/api\/v1\/students\/[^/]+\/enrollments$/)) {
        return BACKEND_MAP.INTEGRATION || ''
    }
    // Default: use college A
    return BACKEND_MAP.A || ''
}

async function fetchXml(path: string, init?: RequestInit) {
    const base = resolveBaseUrl(path)
    const url = base ? `${base}${path}` : path
    const res = await fetch(url, init)
    const text = await res.text()
    return parser.parse(text)
}

async function fetchCollegeXml(collegeId: string, path: string, init?: RequestInit) {
    const base = BACKEND_MAP[collegeId.toUpperCase()] || ''
    const url = base ? `${base}${path}` : path
    const res = await fetch(url, init)
    const text = await res.text()
    return parser.parse(text)
}

export async function fetchSharedCourses() {
    if (MOCK) {
        return localMockSharedCourses()
    }
    try {
        const json = await fetchXml('/api/v1/shared-courses', { headers: { Accept: 'application/xml' } })
        const classes = normalizeArray(json?.Response?.data?.classes?.class).map(normalizeCourse)
        return { classes }
    } catch {
        return { classes: [] }
    }
}

export async function fetchLocalCourses(collegeId: string) {
    if (MOCK) {
        return localMockLocalCoursesFiltered(collegeId)
    }
    try {
        const json = await fetchCollegeXml(collegeId, '/api/v1/courses', { headers: { Accept: 'application/xml' } })
        const classes = normalizeArray(json?.Response?.data?.courses?.course).map(normalizeCourse)
        return { classes }
    } catch {
        return { classes: [] }
    }
}

function formatDateTime(date = new Date()) {
    const pad = (n: number) => String(n).padStart(2, '0')
    const yyyy = date.getFullYear()
    const MM = pad(date.getMonth() + 1)
    const dd = pad(date.getDate())
    const hh = pad(date.getHours())
    const mm = pad(date.getMinutes())
    const ss = pad(date.getSeconds())
    return `${yyyy}-${MM}-${dd} ${hh}:${mm}:${ss}`
}

export async function postEnrollment(sid: string, cid: string, homeCollegeId = '', targetCollegeId = '') {
    if (MOCK) {
        loadMockEnrollments()
        const existing = localMockState.enrollments.find(e => e.sid === sid && e.cid === cid && e.status === 'ENROLLED')
        if (existing) {
            return { code: 409, message: 'duplicate enrollment', data: { enrollmentId: existing.enrollmentId, status: 'EXISTS' } }
        }
        const enrollmentId = `E${Date.now()}`
        const courseName = getCourseName(cid)
        localMockState.enrollments.push({ enrollmentId, cid, sid, status: 'ENROLLED' as const, name: courseName })
        saveMockEnrollments()
        return { code: 0, message: 'success', data: { enrollmentId } }
    }
    const xml = builder.build({
        EnrollmentRequest: {
            meta: { homeCollegeId, targetCollegeId, requestTime: formatDateTime() },
            choices: { choice: { sid, cid, score: 0 } }
        }
    })
    try {
        const json = await fetchXml('/api/v1/enrollments', { method: 'POST', headers: { 'Content-Type': 'application/xml', Accept: 'application/xml' }, body: xml })
        return ensureXmlResponseShape(json)
    } catch (error) {
        return { code: 500, message: error instanceof Error ? error.message : 'enrollment failed', data: {} }
    }
}

export async function withdrawEnrollment(enrollmentId: string, sid = '', cid = '') {
    if (MOCK) {
        loadMockEnrollments()
        const enrollment = localMockState.enrollments.find(e => e.enrollmentId === enrollmentId)
        if (!enrollment) {
            return { code: 404, message: 'enrollment not found', data: { enrollmentId } }
        }
        enrollment.status = 'WITHDRAWN'
        saveMockEnrollments()
        return { code: 0, message: 'withdraw success', data: { enrollmentId, status: 'WITHDRAWN' } }
    }
    const xml = builder.build({
        WithdrawRequest: {
            meta: { requestTime: formatDateTime() },
            choices: { choice: { sid, cid, score: 0 } }
        }
    })
    try {
        const json = await fetchXml(`/api/v1/enrollments/${enrollmentId}/withdraw`, { method: 'POST', headers: { 'Content-Type': 'application/xml', Accept: 'application/xml' }, body: xml })
        return ensureXmlResponseShape(json)
    } catch (error) {
        return { code: 500, message: error instanceof Error ? error.message : 'withdraw failed', data: { enrollmentId } }
    }
}

export async function fetchMyEnrollments(sid: string) {
    if (MOCK) {
        return localMockEnrollments(sid)
    }
    try {
        const json = await fetchXml(`/api/v1/students/${sid}/enrollments`, { headers: { Accept: 'application/xml' } })
        const list = normalizeArray(json?.Response?.data?.enrollments?.enrollment)
        return list.map((item: any) => ({
            enrollmentId: item.enrollmentId || item.id || '',
            cid: item.cid || item.courseId || '',
            name: item.name || getCourseName(item.cid || item.courseId || ''),
            status: item.status || 'ENROLLED',
            sid
        }))
    } catch {
        return []
    }
}

export async function fetchStats() {
    if (MOCK) {
        return localMockStats()
    }
    try {
        const json = await fetchXml('/api/v1/stats/summary', { headers: { Accept: 'application/xml', Authorization: `Bearer ${INTEGRATION_API_KEY}` } })
        const colleges = normalizeArray(json?.Response?.data?.Summary?.college).map((item: any) => ({
            collegeId: item.collegeId || item.collegeID || '',
            studentCount: Number(item.studentCount || 0),
            courseCount: Number(item.courseCount || 0),
            enrollmentCount: Number(item.enrollmentCount || 0)
        }))
        const totals = colleges.reduce(
            (acc, item) => ({
                students: acc.students + item.studentCount,
                courses: acc.courses + item.courseCount,
                enrollments: acc.enrollments + item.enrollmentCount
            }),
            { students: 0, courses: 0, enrollments: 0 }
        )
        return { colleges, totals, categories: localMockStats().categories }
    } catch {
        return { colleges: [], totals: { students: 0, courses: 0, enrollments: 0 }, categories: localMockStats().categories }
    }
}
