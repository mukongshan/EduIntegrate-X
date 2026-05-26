import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchMyEnrollments, withdrawEnrollment } from '../api'

export default function MyEnrollments() {
    const [list, setList] = useState<any[]>([])
    const [msg, setMsg] = useState('')
    const sid = sessionStorage.getItem('sid')
    const { collegeId } = useParams()
    const resolvedCollegeId = collegeId ? collegeId.toUpperCase() : 'A'

    useEffect(() => {
        if (!sid) return
        fetchMyEnrollments(sid).then(data => setList(data || []))
    }, [sid])

    async function withdraw(item: any) {
        setMsg('退选中...')
        const res: any = await withdrawEnrollment(item.enrollmentId, sid || item.sid || '', item.cid || '')
        if (res.code === 0) {
            setMsg('退选成功')
            setList(list.filter(i => i.enrollmentId !== item.enrollmentId))
        } else setMsg(`${res.code}: ${res.message}`)
    }

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-semibold text-slate-950">我的选课</h2>
                <p className="text-sm text-slate-500">查看已选课程与退选状态</p>
            </div>
            {!sid && (
                <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    当前为游客模式，无法查看我的选课，请先 <Link className="font-semibold underline" to={`/college/${resolvedCollegeId}/login`}>登录</Link>。
                </div>
            )}
            {msg && (
                <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
                    {msg}
                </div>
            )}
            {sid && (
                <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                                <tr>
                                    <th className="px-4 py-3">报名号</th>
                                    <th className="px-4 py-3">课程号</th>
                                    <th className="px-4 py-3">名称</th>
                                    <th className="px-4 py-3">状态</th>
                                    <th className="px-4 py-3">操作</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {list.map(i => (
                                    <tr key={i.enrollmentId} className="hover:bg-slate-50">
                                        <td className="px-4 py-3 font-mono text-xs text-slate-500">{i.enrollmentId}</td>
                                        <td className="px-4 py-3 text-slate-600">{i.cid}</td>
                                        <td className="px-4 py-3 font-medium text-slate-950">{i.name}</td>
                                        <td className="px-4 py-3">
                                            <span className="rounded-md bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                                                {i.status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <button
                                                onClick={() => withdraw(i)}
                                                className="rounded-md border border-rose-200 px-4 py-2 text-xs font-semibold text-rose-700 transition hover:bg-rose-50"
                                            >
                                                退选
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    )
}
