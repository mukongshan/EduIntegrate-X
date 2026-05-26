import http from 'http'
import { URL } from 'url'
import { XMLParser, XMLBuilder } from 'fast-xml-parser'

const port = process.env.PORT || 8081

const parser = new XMLParser({ ignoreAttributes: false })
const builder = new XMLBuilder({ ignoreAttributes: false, format: true })

const classes = [
    { id: 'C001', name: '数据库系统', time: 32, score: 3, teacher: '张老师', location: '1-301', collegeId: 'A' },
    { id: 'C018', name: '数据仓库基础', time: 24, score: 2, teacher: '李老师', location: '2-205', collegeId: 'B' },
    { id: 'C023', name: 'XML 数据交换', time: 16, score: 2, teacher: '王老师', location: '3-102', collegeId: 'C' }
]

const localCourses = [
    { id: 'L001', name: '高等数学', time: 48, score: 4, teacher: '赵老师', location: '1-101' },
    { id: 'L002', name: '线性代数', time: 32, score: 3, teacher: '孙老师', location: '1-102' },
    { id: 'L003', name: '概率论', time: 32, score: 3, teacher: '周老师', location: '1-103' },
    { id: 'L004', name: '大学物理', time: 48, score: 4, teacher: '吴老师', location: '2-101' },
    { id: 'L005', name: '计算机导论', time: 24, score: 2, teacher: '郑老师', location: '2-102' }
]

const enrollments = {}
let enrollmentSeq = 1
const users = {
    S2024001: { name: '张三', password: '123456' },
    S2024002: { name: '李四', password: '123456' },
    S2024003: { name: '王五', password: '123456' }
}

function readBody(req) {
    return new Promise(resolve => {
        let data = ''
        req.on('data', chunk => {
            data += chunk
        })
        req.on('end', () => resolve(data))
    })
}

function sendXml(res, code, message, dataObj) {
    const resp = { Response: { code: String(code), message, data: dataObj || {} } }
    const xml = builder.build(resp)
    res.writeHead(code === 0 ? 200 : code, {
        'Content-Type': 'application/xml; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    })
    res.end(xml)
}

function parseEnrollment(xmlText) {
    const parsed = parser.parse(xmlText || '')
    const reqBody = parsed.EnrollmentRequest || parsed.Request || parsed
    const choices = reqBody?.choices?.choice ?? []
    const choice = Array.isArray(choices) ? choices[0] : choices
    return {
        sid: choice?.sid || choice?.Sid || choice?.SID || '',
        cid: choice?.cid || choice?.Cid || choice?.CID || ''
    }
}

function parseLogin(xmlText) {
    const parsed = parser.parse(xmlText || '')
    console.log('[DEBUG] parseLogin parsed:', JSON.stringify(parsed, null, 2))
    const reqBody = parsed.LoginRequest || parsed.Request || parsed
    console.log('[DEBUG] parseLogin reqBody:', JSON.stringify(reqBody, null, 2))
    const result = {
        sid: reqBody?.sid || reqBody?.id || '',
        password: reqBody?.password || ''
    }
    console.log('[DEBUG] parseLogin result:', result)
    return result
}

function findCourseName(cid) {
    return (classes.find(c => c.id === cid) || localCourses.find(c => c.id === cid) || {}).name || ''
}

const server = http.createServer(async (req, res) => {
    const requestUrl = new URL(req.url, `http://${req.headers.host}`)
    const { pathname, searchParams } = requestUrl

    // Handle preflight OPTIONS requests
    if (req.method === 'OPTIONS') {
        res.writeHead(200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
        res.end()
        return
    }

    if (req.method === 'GET' && pathname === '/api/v1/shared-courses') {
        return sendXml(res, 0, 'success', {
            meta: { collegeId: searchParams.get('collegeId') || '' },
            classes: { class: classes }
        })
    }

    if (req.method === 'GET' && pathname.match(/^\/api\/v1\/college\/[ABC]\/courses$/)) {
        return sendXml(res, 0, 'success', {
            classes: { class: localCourses }
        })
    }

    if (req.method === 'POST' && pathname === '/api/v1/enrollments') {
        const body = await readBody(req)
        let sid = ''
        let cid = ''
        try {
            ; ({ sid, cid } = parseEnrollment(body))
        } catch (err) {
            return sendXml(res, 400, 'invalid xml', {})
        }

        for (const id of Object.keys(enrollments)) {
            const e = enrollments[id]
            if (e.sid === sid && e.cid === cid && e.status === 'ENROLLED') {
                return sendXml(res, 409, 'duplicate enrollment', { enrollmentId: e.enrollmentId, status: 'EXISTS' })
            }
        }

        const id = 'E' + String(enrollmentSeq++).padStart(6, '0')
        enrollments[id] = { enrollmentId: id, sid, cid, name: findCourseName(cid), status: 'ENROLLED' }
        return sendXml(res, 0, 'success', { enrollmentId: id })
    }

    if (req.method === 'POST' && pathname === '/api/v1/auth/login') {
        const body = await readBody(req)
        let sid = ''
        let password = ''
        try {
            ; ({ sid, password } = parseLogin(body))
        } catch (err) {
            return sendXml(res, 400, 'invalid xml', {})
        }
        // Convert to string in case XML parser returns number
        const passwordStr = String(password)
        const user = users[sid]
        if (!user || user.password !== passwordStr) {
            console.log(`[LOGIN] Attempt: sid=${sid}, password=${password} (type: ${typeof password}), user found: ${!!user}, password match: ${user && user.password === passwordStr}`)
            return sendXml(res, 401, 'invalid credentials', {})
        }
        console.log(`[LOGIN] Success: sid=${sid}, name=${user.name}`)
        return sendXml(res, 0, 'success', { sid, name: user.name })
    }

    if (req.method === 'POST' && pathname.startsWith('/api/v1/enrollments/') && pathname.endsWith('/withdraw')) {
        const enrollmentId = pathname.split('/')[4]
        if (!enrollments[enrollmentId]) {
            return sendXml(res, 404, 'enrollment not found', { enrollmentId })
        }
        enrollments[enrollmentId].status = 'WITHDRAWN'
        return sendXml(res, 0, 'withdraw writeback success', { enrollmentId, status: 'WITHDRAWN' })
    }

    if (req.method === 'GET' && pathname === '/api/v1/stats/summary') {
        const active = Object.values(enrollments).filter(e => e.status === 'ENROLLED').length
        return sendXml(res, 0, 'success', {
            Summary: {
                college: [
                    { collegeId: 'A', studentCount: 50, courseCount: 10, enrollmentCount: Math.floor(active / 3), sharedCourseCount: 2, incomingEnrollments: 8 },
                    { collegeId: 'B', studentCount: 50, courseCount: 10, enrollmentCount: Math.floor(active / 3), sharedCourseCount: 3, incomingEnrollments: 12 },
                    { collegeId: 'C', studentCount: 50, courseCount: 10, enrollmentCount: active - Math.floor(active / 3) * 2, sharedCourseCount: 1, incomingEnrollments: 5 }
                ]
            }
        })
    }

    if (req.method === 'GET' && pathname.match(/^\/api\/v1\/students\/[^/]+\/enrollments$/)) {
        const sid = pathname.split('/')[4]
        const list = Object.values(enrollments)
            .filter(e => e.sid === sid)
            .map(e => ({ enrollmentId: e.enrollmentId, cid: e.cid, name: e.name || findCourseName(e.cid), status: e.status }))
        return sendXml(res, 0, 'success', { enrollments: { enrollment: list } })
    }

    res.writeHead(404, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Access-Control-Allow-Origin': '*'
    })
    res.end('Not Found')
})

server.listen(port, () => {
    console.log(`Mock server running at http://localhost:${port}`)
})
