import React, { useState, useEffect } from 'react'
import { fetchStats } from '../api'
import { Layers3, Users, BarChart3, Radio, RefreshCcw, Wifi, BookOpen, ArrowUpRight, Award } from 'lucide-react'

type CollegeId = 'A' | 'B' | 'C'

// 扩展后的各学院统计接口声明
interface SummaryElement {
    collegeId: CollegeId
    studentCount: number
    courseCount: number
    enrollmentCount: number
    sharedCourseCount?: number     // 新增扩展：该学院向外提供的共享课程数
    incomingEnrollments?: number   // 新增扩展：其他学院学生选修该院共享课的总人次
}

// 新增：共享课程按类别/领域划分的跨院选课统计
interface SharedCategoryStat {
    category: string
    enrollmentCount: number
    percentage: number
}

const COLLEGE_CONFIG = {
    A: { name: '学院 A 门户', dbType: 'SQL Server', icon: 'bg-blue-600' },
    B: { name: '学院 B 门户', dbType: 'Oracle', icon: 'bg-emerald-600' },
    C: { name: '学院 C 门户', dbType: 'MySQL', icon: 'bg-orange-600' },
}

interface KpiCardProps {
    title: string
    value: number
    xsd: string
    icon: React.ReactNode
    theme: 'blue' | 'green' | 'orange'
}

const KpiCard: React.FC<KpiCardProps> = ({ title, value, xsd, icon, theme }) => {
    const themeMap = {
        blue: 'text-blue-600 bg-blue-50 border-blue-100',
        green: 'text-emerald-600 bg-emerald-50 border-emerald-100',
        orange: 'text-orange-600 bg-orange-50 border-orange-100',
    }

    return (
        <div className="surface group relative overflow-hidden rounded-xl p-6 transition hover:-translate-y-1 hover:shadow-lg">
            <div className="relative z-10 mb-6 flex items-center justify-between">
                <div className="text-sm font-semibold text-slate-500">{title}</div>
                <div className={`rounded-lg border p-2 ${themeMap[theme]}`}>
                    {icon}
                </div>
            </div>
            <div className="relative z-10 mb-1 flex items-end gap-3">
                <div className="animate-fade-in text-4xl font-extrabold tracking-tight text-slate-950 tabular-nums">
                    {value.toLocaleString()}
                </div>
                <div className="pb-1 text-sm text-slate-500">{title.includes('学生') ? '人' : title.includes('课程') ? '节' : '次'}</div>
            </div>
            <div className="relative z-10 mt-4 flex items-center gap-2 text-xs text-slate-500">
                <Layers3 className="h-4 w-4 text-slate-400" />
                来自统一 XML Schema: {xsd}
            </div>
        </div>
    )
}

export default function StatsView() {
    // 状态定义：包含学院基础数据、全局汇总及新增的共享课程类别数据
    const [stats, setStats] = useState<{
        colleges: SummaryElement[];
        totals: { students: number; courses: number; enrollments: number };
        categories: SharedCategoryStat[];
    } | null>(null)
    const [loading, setLoading] = useState(false)

    // 封装真实的后端数据请求逻辑
    const loadBackendData = async () => {
        try {
            const data = await fetchStats()
            setStats(data)
        } catch (error) {
            console.error("后端集成数据同步失败:", error)
        }
    }

    useEffect(() => {
        loadBackendData()
    }, [])

    // 真实的按钮刷新逻辑：不再调用 Math.random()，而是重新向后端接口发起 HTTP GET 请求
    const handleRefresh = async () => {
        setLoading(true)
        await loadBackendData()
        // 增加短暂延时增强刷新的视觉反馈感
        setTimeout(() => setLoading(false), 600)
    }

    if (!stats) return <div className="app-shell flex min-h-screen items-center justify-center text-slate-600">加载后端真实数据库中...</div>

    const { colleges, totals, categories = [] } = stats
    const totalStudents = totals.students

    return (
        <div className="app-shell min-h-screen p-6 font-sans text-slate-900 md:p-10">

            {/* 头部区域 */}
            <header className="surface mb-8 flex flex-wrap items-center justify-between gap-4 rounded-xl p-6">
                <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-950 text-white">
                        <Layers3 className="h-6 w-6" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-extrabold tracking-tight text-slate-950">EduIntegrate 数据集成工作台</h1>
                        <p className="mt-1 flex items-center gap-2 text-sm text-slate-500">
                            <Wifi className={`w-4 h-4 ${loading ? 'text-orange-400 animate-pulse' : 'text-green-400'}`} />
                            集成服务器 (10.60.254.43:8080) 状态监控
                        </p>
                    </div>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={loading}
                    className="flex items-center gap-2 rounded-lg bg-slate-950 px-5 py-3 text-sm font-semibold text-white shadow-sm transition-all active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 hover:bg-slate-800"
                >
                    <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    刷新后端数据同步
                </button>
            </header>

            {/* KPI 核心指标卡片区 */}
            <section className="mb-8 grid grid-cols-1 gap-5 md:grid-cols-3">
                <KpiCard
                    title="汇总学生总数"
                    value={totalStudents}
                    xsd="formatStudent.xsd"
                    icon={<Users className="w-10 h-10 text-blue-400" />}
                    theme="blue"
                />
                <KpiCard
                    title="三院课程总数"
                    value={totals.courses}
                    xsd="formatClass.xsd"
                    icon={<BarChart3 className="w-10 h-10 text-emerald-400" />}
                    theme="green"
                />
                <KpiCard
                    title="选课记录总次数 (含跨院)"
                    value={totals.enrollments}
                    xsd="formatClassChoice.xsd"
                    icon={<Radio className="w-10 h-10 text-orange-400" />}
                    theme="orange"
                />
            </section>

            {/* 主数据看板网格 */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">

                {/* 左侧：各学院异构数据库分布式数据量 (2/3宽度) */}
                <div className="surface relative rounded-xl p-6 xl:col-span-2">
                    <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
                        <div>
                            <h2 className="text-xl font-bold tracking-tight text-slate-950">各学院异构数据库分布情况</h2>
                            <p className="mt-1 text-sm text-slate-500">展示通过集成中间件统一清洗与映射后的本地节点数据规模</p>
                        </div>
                        <div className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
                            XML 异构映射适配层正常
                        </div>
                    </div>

                    <div className="space-y-6">
                        {colleges.map((item) => {
                            const config = COLLEGE_CONFIG[item.collegeId] || { name: `学院 ${item.collegeId}`, dbType: 'Unknown', icon: 'bg-slate-600' }
                            const studentPercentage = totalStudents > 0 ? Math.round((item.studentCount / totalStudents) * 100) : 0

                            return (
                                <div key={item.collegeId} className="group relative rounded-xl border border-slate-200 bg-slate-50/70 p-5 transition hover:bg-white hover:shadow-sm">
                                    <div className="mb-3 flex items-center justify-between gap-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-3 h-3 rounded-full ${config.icon}`}></div>
                                            <span className="text-base font-bold text-slate-950">{config.name}</span>
                                            <span className="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs font-semibold text-slate-500">
                                                {config.dbType}
                                            </span>
                                        </div>
                                        <div className="flex items-end gap-2 text-right">
                                            <div className="text-xl font-bold text-slate-950">{item.studentCount} 本科生</div>
                                            <div className="pb-0.5 text-xs text-slate-500">({studentPercentage}%)</div>
                                        </div>
                                    </div>

                                    {/* 学生人数比例条 */}
                                    <div className="relative h-2 w-full overflow-hidden rounded-full border border-slate-200 bg-white">
                                        <div
                                            className={`absolute top-0 left-0 h-full rounded-full bg-gradient-to-r ${config.icon.replace('bg', 'from')} to-white/40 transition-all duration-500`}
                                            style={{ width: `${studentPercentage}%` }}
                                        ></div>
                                    </div>

                                    {/* 下方明细：重点突出了共享课程和跨院被选的数据流向 */}
                                    <div className="mt-4 grid grid-cols-2 gap-3 border-t border-slate-200 pt-3 text-xs text-slate-500 md:grid-cols-4">
                                        <div>本院总课数: <span className="font-bold text-slate-900">{item.courseCount}</span></div>
                                        <div>本院选课量: <span className="font-bold text-slate-900">{item.enrollmentCount}</span></div>
                                        <div className="text-blue-600">对外共享课: <span className="font-bold">{item.sharedCourseCount || 0} 门</span></div>
                                        <div className="text-orange-600">跨院被选量: <span className="font-bold">{item.incomingEnrollments || 0} 人次</span></div>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>

                {/* 右侧：用全新的“共享课程分类与选课热度统计”替换原来的冗余写回按钮 (1/3宽度) */}
                <div className="surface flex flex-col rounded-xl p-6">
                    <div className="mb-6">
                        <h2 className="text-xl font-bold tracking-tight text-slate-950">共享课程跨院交互看板</h2>
                        <p className="mt-1 text-sm text-slate-500">共享课程在不同学术领域的分类热度排行</p>
                    </div>

                    <div className="space-y-5 flex-1 overflow-y-auto pr-1">
                        {categories.length === 0 ? (
                            <div className="py-10 text-center text-sm text-slate-500">
                                暂无共享课程分类选课数据，请检查后端 XSD 转换层。
                            </div>
                        ) : (
                            categories.map((cat, index) => (
                                <div key={index} className="group rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:bg-white hover:shadow-sm">
                                    <div className="mb-2 flex items-center justify-between gap-3">
                                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                                            {index === 0 ? (
                                                <Award className="w-4 h-4 text-yellow-500 flex-shrink-0" />
                                            ) : (
                                                <BookOpen className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                                            )}
                                            <span className="truncate">{cat.category}</span>
                                        </div>
                                        <div className="flex items-center gap-1 text-xs font-semibold text-blue-600">
                                            <span>{cat.enrollmentCount}人选</span>
                                            <ArrowUpRight className="w-3 h-3 text-slate-500 group-hover:text-cyan-400 transition-colors" />
                                        </div>
                                    </div>

                                    {/* 类别占比进度条 */}
                                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white">
                                        <div
                                            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-500"
                                            style={{ width: `${cat.percentage}%` }}
                                        ></div>
                                    </div>
                                    <div className="mt-1 text-right text-[10px] text-slate-500">
                                        占跨院选课总量 {cat.percentage}%
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    <div className="mt-6 border-t border-slate-200 pt-4 text-xs leading-relaxed text-slate-500">
                        数据源自中间件对 XML Schema (formatClassChoice.xsd) 报文的分类解包与联席查询。
                    </div>
                </div>

            </div>
        </div>
    )
}
