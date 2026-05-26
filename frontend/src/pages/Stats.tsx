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
        blue: 'border-blue-900/50 hover:border-blue-700 hover:shadow-blue-950/40 text-blue-400',
        green: 'border-emerald-900/50 hover:border-emerald-700 hover:shadow-emerald-950/40 text-emerald-400',
        orange: 'border-orange-900/50 hover:border-orange-700 hover:shadow-orange-950/40 text-orange-400',
    }

    return (
        <div className={`group bg-slate-900 p-8 rounded-3xl shadow-xl transition-all duration-300 ease-out border-2 hover:-translate-y-2 hover:shadow-2xl ${themeMap[theme]} relative overflow-hidden`}>
            <div className="flex justify-between items-center mb-6 relative z-10">
                <div className="text-slate-400 text-sm font-semibold tracking-wider uppercase">{title}</div>
                <div className="absolute top-0 right-0 opacity-10 group-hover:opacity-20 group-hover:scale-120 transition-all duration-500">
                    {icon}
                </div>
            </div>
            <div className="relative z-10 flex items-end gap-3 mb-1">
                <div className="text-6xl font-extrabold tracking-tight text-slate-50 tabular-nums animate-fade-in">
                    {value.toLocaleString()}
                </div>
                <div className="text-sm text-slate-500 pb-1.5 font-mono">{title.includes('学生') ? '人' : title.includes('课程') ? '节' : '次'}</div>
            </div>
            <div className="text-sm text-slate-500 flex items-center gap-2 mt-4 relative z-10 group-hover:text-slate-300">
                <Layers3 className="w-4 h-4 text-slate-600 group-hover:text-cyan-600" />
                来自统一 XML Schema: {xsd}
            </div>
            <div className={`absolute -bottom-10 -right-10 w-40 h-40 rounded-full ${themeMap[theme].split(' ')[0]} blur-3xl opacity-20 group-hover:opacity-30 group-hover:scale-150 transition-all duration-500`}></div>
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

    if (!stats) return <div className="min-h-screen bg-slate-950 text-slate-200 flex items-center justify-center">加载后端真实数据库中...</div>

    const { colleges, totals, categories = [] } = stats
    const totalStudents = totals.students

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans p-6 md:p-10">

            {/* 头部区域 */}
            <header className="flex justify-between items-center mb-10 pb-6 border-b border-slate-800">
                <div className="flex items-center gap-4">
                    <Layers3 className="w-10 h-10 text-cyan-400" />
                    <div>
                        <h1 className="text-3xl font-extrabold tracking-tight">EduIntegrate 数据集成中心大屏</h1>
                        <p className="text-slate-400 mt-1 flex items-center gap-2">
                            <Wifi className={`w-4 h-4 ${loading ? 'text-orange-400 animate-pulse' : 'text-green-400'}`} />
                            集成服务器 (10.60.254.43:8080) 状态监控
                        </p>
                    </div>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={loading}
                    className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 px-5 py-3 rounded-xl shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 text-sm font-semibold"
                >
                    <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    刷新后端数据同步
                </button>
            </header>

            {/* KPI 核心指标卡片区 */}
            <section className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
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
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-10">

                {/* 左侧：各学院异构数据库分布式数据量 (2/3宽度) */}
                <div className="xl:col-span-2 bg-slate-900 p-8 rounded-2xl shadow-xl border border-slate-800 relative">
                    <div className="flex justify-between items-start mb-8">
                        <div>
                            <h2 className="text-2xl font-bold tracking-tight">各学院异构数据库分布情况</h2>
                            <p className="text-sm text-slate-400 mt-1">展示通过集成中间件统一清洗与映射后的本地节点数据规模</p>
                        </div>
                        <div className="text-xs text-slate-400 bg-slate-800 px-3 py-1.5 rounded-full font-mono">
                            XML 异构映射适配层正常
                        </div>
                    </div>

                    <div className="space-y-6">
                        {colleges.map((item) => {
                            const config = COLLEGE_CONFIG[item.collegeId] || { name: `学院 ${item.collegeId}`, dbType: 'Unknown', icon: 'bg-slate-600' }
                            const studentPercentage = totalStudents > 0 ? Math.round((item.studentCount / totalStudents) * 100) : 0

                            return (
                                <div key={item.collegeId} className="group relative bg-slate-800/30 p-5 rounded-xl border border-slate-700/60 transition-all hover:bg-slate-800/80 hover:shadow-lg">
                                    <div className="flex justify-between items-center mb-3">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-3 h-3 rounded-full ${config.icon}`}></div>
                                            <span className="font-bold text-base text-slate-100">{config.name}</span>
                                            <span className="text-xs text-cyan-500 font-mono bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                                                {config.dbType}
                                            </span>
                                        </div>
                                        <div className="text-right flex items-end gap-2">
                                            <div className="text-xl font-bold text-slate-100">{item.studentCount} 本科生</div>
                                            <div className="text-xs text-slate-500 font-mono pb-0.5">({studentPercentage}%)</div>
                                        </div>
                                    </div>

                                    {/* 学生人数比例条 */}
                                    <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden relative border border-slate-800">
                                        <div
                                            className={`absolute top-0 left-0 h-full rounded-full bg-gradient-to-r ${config.icon.replace('bg', 'from')} to-white/40 transition-all duration-500`}
                                            style={{ width: `${studentPercentage}%` }}
                                        ></div>
                                    </div>

                                    {/* 下方明细：重点突出了共享课程和跨院被选的数据流向 */}
                                    <div className="grid grid-cols-4 mt-4 pt-3 border-t border-slate-800/60 text-xs font-mono text-slate-400">
                                        <div>本院总课数: <span className="text-slate-200 font-bold">{item.courseCount}</span></div>
                                        <div>本院选课量: <span className="text-slate-200 font-bold">{item.enrollmentCount}</span></div>
                                        <div className="text-cyan-400">对外共享课: <span className="font-bold text-cyan-300">{item.sharedCourseCount || 0} 门</span></div>
                                        <div className="text-orange-400">跨院被选量: <span className="font-bold text-orange-300">{item.incomingEnrollments || 0} 人次</span></div>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>

                {/* 右侧：用全新的“共享课程分类与选课热度统计”替换原来的冗余写回按钮 (1/3宽度) */}
                <div className="bg-slate-900 p-8 rounded-2xl shadow-xl border border-slate-800 flex flex-col">
                    <div className="mb-6">
                        <h2 className="text-2xl font-bold tracking-tight">共享课程跨院交互看板</h2>
                        <p className="text-sm text-slate-400 mt-1">核心系统集成成果：共享课程在不同学术领域的分类热度排行</p>
                    </div>

                    <div className="space-y-5 flex-1 overflow-y-auto pr-1">
                        {categories.length === 0 ? (
                            <div className="text-slate-500 text-sm italic text-center py-10">
                                暂无共享课程分类选课数据，请检查后端 XSD 转换层。
                            </div>
                        ) : (
                            categories.map((cat, index) => (
                                <div key={index} className="bg-slate-950 p-4 rounded-xl border border-slate-800/80 group hover:border-slate-700 transition-all">
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                                            {index === 0 ? (
                                                <Award className="w-4 h-4 text-yellow-500 flex-shrink-0" />
                                            ) : (
                                                <BookOpen className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                                            )}
                                            <span className="truncate">{cat.category}</span>
                                        </div>
                                        <div className="text-xs font-mono text-cyan-400 flex items-center gap-1">
                                            <span>{cat.enrollmentCount}人选</span>
                                            <ArrowUpRight className="w-3 h-3 text-slate-500 group-hover:text-cyan-400 transition-colors" />
                                        </div>
                                    </div>

                                    {/* 类别占比进度条 */}
                                    <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                                        <div
                                            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-500"
                                            style={{ width: `${cat.percentage}%` }}
                                        ></div>
                                    </div>
                                    <div className="text-[10px] text-right font-mono text-slate-500 mt-1">
                                        占跨院选课总量 {cat.percentage}%
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    <div className="border-t border-slate-800 mt-6 pt-4 text-xs text-slate-500 leading-relaxed font-mono">
                        数据源自中间件对 XML Schema (formatClassChoice.xsd) 报文的分类解包与联席查询。
                    </div>
                </div>

            </div>
        </div>
    )
}
