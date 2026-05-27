import React, { useEffect, useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { fetchLocalCourses, fetchSharedCourses, postEnrollment, fetchMyEnrollments } from '../api'
import { BookOpen, CheckCircle2, Globe2, Search } from 'lucide-react'

type Course = { id: string; name: string; time: number; score: number; teacher: string; location: string; collegeId?: string }
type Enrollment = { enrollmentId: string; cid: string; name: string; status: string; sid: string }

export default function Courses() {
    const [tab, setTab] = useState<'local' | 'shared'>('local')
    const [courses, setCourses] = useState<Course[]>([])
    const [enrolledIds, setEnrolledIds] = useState<Set<string>>(new Set())
    const [search, setSearch] = useState('')
    const [message, setMessage] = useState('')
    const navigate = useNavigate()
    const { collegeId } = useParams()
    const resolvedCollegeId = collegeId ? collegeId.toUpperCase() : 'A'

    const location = useLocation()

    const sid = sessionStorage.getItem('sid')
    const isLoggedIn = !!sid

    useEffect(() => {
        loadCourses()
    }, [tab, resolvedCollegeId])

    // Initialize tab from query param ?tab=local|shared
    useEffect(() => {
        const q = new URLSearchParams(location.search).get('tab')
        if (q === 'shared' || q === 'local') {
            setTab(q)
        }
    }, [location.search])

    useEffect(() => {
        if (sid) {
            fetchMyEnrollments(sid).then((data: Enrollment[]) => {
                const active = data.filter((e: Enrollment) => e.status === 'ENROLLED')
                setEnrolledIds(new Set(active.map((e: Enrollment) => e.cid)))
            })
        }
    }, [sid, courses])

    async function loadCourses() {
        let data: { classes: Course[] }
        if (tab === 'local') {
            data = await fetchLocalCourses(resolvedCollegeId)
        } else {
            data = await fetchSharedCourses()
        }
        setCourses(data.classes || [])
    }

    function filteredCourses() {
        if (!search) return courses
        const q = search.toLowerCase()
        return courses.filter(c =>
            (c.id || '').toLowerCase().includes(q) ||
            (c.name || '').toLowerCase().includes(q) ||
            (c.teacher || '').toLowerCase().includes(q)
        )
    }

    async function enroll(cid: string) {
        if (!isLoggedIn) {
            setMessage('请先登录后再选课')
            navigate(`/college/${resolvedCollegeId}/login`)
            return
        }
        setMessage('提交中...')
        const course = courses.find(item => item.id === cid)
        const targetCollegeId = course?.collegeId || resolvedCollegeId
        const res: any = await postEnrollment(sid!, cid, resolvedCollegeId, targetCollegeId)
        if (res.code === 0) {
            setMessage(`选课成功：${res.data.enrollmentId}`)
            setEnrolledIds(prev => new Set([...prev, cid]))
        } else {
            setMessage(`${res.code}: ${res.message}`)
        }
    }

    return (
        <div className="space-y-6">
            <div className="surface rounded-xl p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-semibold tracking-tight text-slate-950">课程列表</h2>
                    <p className="text-sm text-slate-500">支持本院与跨院共享课程查询</p>
                </div>
                <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-1">
                    <button
                        className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition ${tab === 'local' ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-600 hover:text-slate-950'}`}
                        onClick={() => setTab('local')}
                    >
                        <BookOpen className="h-4 w-4" />
                        本院课程
                    </button>
                    <button
                        className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition ${tab === 'shared' ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-600 hover:text-slate-950'}`}
                        onClick={() => setTab('shared')}
                    >
                        <Globe2 className="h-4 w-4" />
                        共享课程
                    </button>
                </div>
                </div>
            </div>

            {message && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-900">
                    {message}
                </div>
            )}

            <div className="surface flex items-center gap-3 rounded-xl px-4 py-3">
                <Search className="h-4 w-4 text-slate-400" />
                <input
                    type="text"
                    placeholder="搜索课程号、名称或教师..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="w-full bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
                />
            </div>

            <div className="surface overflow-hidden rounded-xl">
                <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead className="bg-slate-50/90 text-left text-xs uppercase text-slate-500">
                            <tr>
                                <th className="px-4 py-3">课程号</th>
                                <th className="px-4 py-3">名称</th>
                                <th className="px-4 py-3">学时</th>
                                <th className="px-4 py-3">学分</th>
                                <th className="px-4 py-3">教师</th>
                                <th className="px-4 py-3">地点</th>
                                {tab === 'shared' && <th className="px-4 py-3">开课学院</th>}
                                <th className="px-4 py-3">操作</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {filteredCourses().map(c => {
                                const enrolled = enrolledIds.has(c.id)
                                return (
                                    <tr key={c.id} className="transition hover:bg-slate-50">
                                        <td className="px-4 py-3 font-mono text-xs text-slate-500">{c.id}</td>
                                        <td className="px-4 py-3 font-medium text-slate-950">
                                            {enrolled && (
                                                <span className="mr-2 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-300">
                                                    <CheckCircle2 className="mr-1 inline h-3 w-3" />
                                                    已选
                                                </span>
                                            )}
                                            {c.name || '未命名课程'}
                                        </td>
                                        <td className="px-4 py-3 text-slate-600">{c.time}</td>
                                        <td className="px-4 py-3 text-slate-600">{c.score}</td>
                                        <td className="px-4 py-3 text-slate-600">{c.teacher}</td>
                                        <td className="px-4 py-3 text-slate-600">{c.location}</td>
                                        {tab === 'shared' && <td className="px-4 py-3 text-slate-600">{c.collegeId || '-'}</td>}
                                        <td className="px-4 py-3">
                                            <button
                                                onClick={() => enroll(c.id)}
                                                disabled={enrolled}
                                                className={`rounded-lg px-4 py-2 text-xs font-semibold transition ${enrolled ? 'cursor-not-allowed bg-slate-100 text-slate-400' : 'text-white shadow-sm hover:-translate-y-0.5'}`}
                                                style={enrolled ? undefined : { background: 'var(--theme)' }}
                                            >
                                                {enrolled ? '已选' : '选课'}
                                            </button>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {filteredCourses().length === 0 && (
                <div className="surface rounded-xl px-4 py-5 text-center text-sm text-slate-500">
                    暂无课程
                </div>
            )}
        </div>
    )
}
