import React, { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { loginWithPassword } from '../api'

export default function Login() {
    const [sid, setSid] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')
    const navigate = useNavigate()
    const { collegeId } = useParams()
    const resolvedCollegeId = collegeId ? collegeId.toUpperCase() : 'A'

    async function handleLogin(e: React.FormEvent) {
        e.preventDefault()
        const res = await loginWithPassword(sid, password)
        if (res.code !== 0) {
            setError('学号或密码错误')
            return
        }
        sessionStorage.setItem('sid', res.data.sid)
        sessionStorage.setItem('name', res.data.name)
        sessionStorage.removeItem('college')
        setError('')
        navigate(`/college/${resolvedCollegeId}/courses`)
    }

    return (
        <div className="mx-auto max-w-md rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
            <div className="mb-6">
                <h2 className="text-2xl font-semibold text-slate-950">账户登录</h2>
                <p className="text-sm text-slate-500">请输入学号与密码进入选课系统</p>
            </div>
            <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-600">学号 / 账号</label>
                    <input
                        value={sid}
                        onChange={e => setSid(e.target.value)}
                        className="w-full rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-300"
                    />
                </div>
                <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-600">密码</label>
                    <div className="relative">
                        <input
                            type={showPassword ? 'text' : 'password'}
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            className="w-full rounded-md border border-slate-200 bg-white px-4 py-3 pr-16 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-300"
                        />
                        <button
                            type="button"
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500 hover:text-slate-900"
                            onClick={() => setShowPassword(prev => !prev)}
                            aria-label={showPassword ? '隐藏密码' : '显示密码'}
                        >
                            {showPassword ? '隐藏' : '显示'}
                        </button>
                    </div>
                </div>
                {error && (
                    <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                        {error}
                    </div>
                )}
                <button
                    type="submit"
                    className="w-full rounded-md bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-800"
                >
                    登录
                </button>
            </form>
        </div>
    )
}
