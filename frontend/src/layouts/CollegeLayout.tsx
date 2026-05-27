import React, { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useParams } from 'react-router-dom'
import { GraduationCap, LogIn, UserRound } from 'lucide-react'

const THEMES: Record<string, { title: string; color: string }> = {
    A: { title: '学院 A 选课系统', color: '#2563eb' },
    B: { title: '学院 B 选课系统', color: '#10b981' },
    C: { title: '学院 C 选课系统', color: '#f97316' }
}

function normalizeCollegeId(value: string | undefined) {
    if (!value) return 'A'
    const upper = value.toUpperCase()
    return ['A', 'B', 'C'].includes(upper) ? upper : 'A'
}

export default function CollegeLayout() {
    const { collegeId } = useParams()
    const resolvedId = normalizeCollegeId(collegeId)
    const theme = THEMES[resolvedId]
    const [name, setName] = useState(sessionStorage.getItem('name'))

    useEffect(() => {
        document.documentElement.style.setProperty('--theme', theme.color)
    }, [theme.color])

    // 监听 collegeId 变化，如果变化则清除登陆状态
    useEffect(() => {
        const lastCollegeId = sessionStorage.getItem('lastCollegeId')
        if (lastCollegeId && lastCollegeId !== resolvedId) {
            // 学院 ID 变化，清除登陆状态
            sessionStorage.removeItem('sid')
            sessionStorage.removeItem('name')
            setName(null)
        }
        sessionStorage.setItem('lastCollegeId', resolvedId)
    }, [resolvedId])

    return (
        <div className="app-shell min-h-screen text-slate-900">
            <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
                <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-3">
                    <div className="flex items-center gap-3">
                        <div
                            className="flex h-10 w-10 items-center justify-center rounded-lg text-white shadow-sm ring-1 ring-black/5"
                            style={{ background: theme.color }}
                        >
                            <GraduationCap className="h-5 w-5" />
                        </div>
                        <div>
                            <div className="text-base font-semibold leading-tight text-slate-950">{theme.title}</div>
                            <div className="text-xs text-slate-500">XML 异构教务集成门户</div>
                        </div>
                    </div>
                    <nav className="flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50/80 p-1 text-sm">
                        {[
                            [`/college/${resolvedId}`, '首页'],
                            [`/college/${resolvedId}/courses`, '课程'],
                            [`/college/${resolvedId}/enrollments`, '我的选课']
                        ].map(([to, label]) => (
                            <NavLink
                                key={to}
                                end={label === '首页'}
                                className={({ isActive }) =>
                                    `rounded-md px-3 py-2 font-medium transition ${isActive ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-600 hover:bg-white/70 hover:text-slate-950'}`
                                }
                                to={to}
                            >
                                {label}
                            </NavLink>
                        ))}
                        <Link className="ml-1 inline-flex items-center gap-2 rounded-md px-3 py-2 font-medium text-slate-700 hover:bg-white hover:text-slate-950" to={`/college/${resolvedId}/login`}>
                            <LogIn className="h-4 w-4" />
                            {name ? '切换用户' : '登录'}
                        </Link>
                    </nav>
                    <div className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm">
                        <UserRound className="h-4 w-4" />
                        {name ? name : '访客'}
                    </div>
                </div>
            </header>
            <main className="mx-auto w-full max-w-7xl px-6 pb-16 pt-8">
                <Outlet />
            </main>
        </div>
    )
}
