import React from 'react'
import { Link, useParams } from 'react-router-dom'
import { BookOpen, Globe, ClipboardList, ArrowRight, User, Lock } from 'lucide-react'

const THEMES: Record<string, { title: string; color: string; gradient: string; greeting: string }> = {
    A: { title: '学院 A 选课系统', color: '#2563eb', gradient: 'from-blue-600 to-blue-900', greeting: '欢迎来到学院 A' },
    B: { title: '学院 B 选课系统', color: '#10b981', gradient: 'from-emerald-600 to-emerald-900', greeting: '欢迎来到学院 B' },
    C: { title: '学院 C 选课系统', color: '#f97316', gradient: 'from-orange-600 to-orange-900', greeting: '欢迎来到学院 C' }
}

function normalizeCollegeId(value: string | undefined) {
    if (!value) return 'A'
    const upper = value.toUpperCase()
    return ['A', 'B', 'C'].includes(upper) ? upper : 'A'
}

export default function Home() {
    const { collegeId } = useParams()
    const resolvedId = normalizeCollegeId(collegeId)
    const theme = THEMES[resolvedId]
    const name = sessionStorage.getItem('name')
    const sid = sessionStorage.getItem('sid')
    const isLoggedIn = !!name

    return (
        <div className="space-y-8">
            <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
                <div className="grid gap-6 p-8 lg:grid-cols-[1.4fr_0.8fr] lg:items-center">
                    <div className="space-y-6">
                    <div className="flex items-center gap-3">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg text-white" style={{ background: theme.color }}>
                            <BookOpen className="h-6 w-6" />
                        </div>
                        <div>
                            <div className="text-xs font-semibold uppercase text-slate-500">EduIntegrate</div>
                            <h1 className="text-3xl font-bold text-slate-950">{theme.title}</h1>
                            <p className="text-sm text-slate-500">异构数据库集成 · 统一 XML Schema 交换</p>
                        </div>
                    </div>

                    {isLoggedIn ? (
                        <div className="inline-flex flex-wrap items-center gap-3 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-900">
                            <User className="h-4 w-4" />
                            <span className="font-semibold">你好，{name}</span>
                            <span className="text-emerald-700">（{sid}）</span>
                            <span className="text-sm text-emerald-700">已登录，可直接选课</span>
                        </div>
                    ) : (
                        <div className="inline-flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                            <Lock className="h-4 w-4" />
                            登录后可进行选课、退课等操作
                        </div>
                    )}

                    <div className="flex flex-wrap gap-4">
                        <Link
                            to={`/college/${resolvedId}/courses`}
                            className="inline-flex items-center gap-2 rounded-md px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5"
                            style={{ background: theme.color }}
                        >
                            进入选课
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                        {!isLoggedIn && (
                            <Link
                                to={`/college/${resolvedId}/login`}
                                className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:-translate-y-0.5 hover:bg-slate-50"
                            >
                                登录
                            </Link>
                        )}
                    </div>
                    </div>
                    <div className="grid gap-3 rounded-lg bg-slate-50 p-5">
                        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                            <span className="text-sm text-slate-500">当前学院</span>
                            <span className="text-lg font-bold text-slate-950">{resolvedId}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                            <div className="rounded-md bg-white p-3">
                                <div className="text-slate-500">交换格式</div>
                                <div className="mt-1 font-semibold text-slate-900">application/xml</div>
                            </div>
                            <div className="rounded-md bg-white p-3">
                                <div className="text-slate-500">业务流程</div>
                                <div className="mt-1 font-semibold text-slate-900">选课 / 退课</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* 功能卡片 */}
            <div className="grid gap-6 md:grid-cols-3">

                <Link to={`/college/${resolvedId}/courses?tab=local`} className="group rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-md">
                    <div className="w-11 h-11 rounded-md bg-blue-50 flex items-center justify-center mb-4">
                        <BookOpen className="w-6 h-6 text-blue-400" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-950 mb-2">本院课程</h3>
                    <p className="text-slate-500 text-sm mb-4">查看并选修本院开设的所有课程，涵盖各专业核心课程</p>
                    <div className="flex items-center gap-2 text-blue-400 text-sm font-semibold group-hover:text-blue-300">
                        查看课程 <ArrowRight className="w-4 h-4" />
                    </div>
                </Link>

                <Link to={`/college/${resolvedId}/courses?tab=shared`} className="group rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-emerald-200 hover:shadow-md">
                    <div className="w-11 h-11 rounded-md bg-emerald-50 flex items-center justify-center mb-4">
                        <Globe className="w-6 h-6 text-emerald-400" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-950 mb-2">共享课程</h3>
                    <p className="text-slate-500 text-sm mb-4">跨院选修其他学院的开放课程，拓宽学习视野，探索跨学科领域</p>
                    <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold group-hover:text-emerald-300">
                        查看课程 <ArrowRight className="w-4 h-4" />
                    </div>
                </Link>

                <Link to={`/college/${resolvedId}/enrollments`} className="group rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-orange-200 hover:shadow-md">
                    <div className="w-11 h-11 rounded-md bg-orange-50 flex items-center justify-center mb-4">
                        <ClipboardList className="w-6 h-6 text-orange-400" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-950 mb-2">我的选课</h3>
                    <p className="text-slate-500 text-sm mb-4">查看已选课程，进行退课操作，管理个人课表</p>
                    <div className="flex items-center gap-2 text-orange-400 text-sm font-semibold group-hover:text-orange-300">
                        查看详情 <ArrowRight className="w-4 h-4" />
                    </div>
                </Link>

            </div>

            {/* 底部提示 */}
            <div className="text-center text-sm text-slate-500">
                <p>基于 XML Schema 统一交换 · 三院异构数据库互联互通</p>
            </div>
        </div>
    )
}
