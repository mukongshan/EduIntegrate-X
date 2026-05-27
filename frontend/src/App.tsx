import React, { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, Link } from 'react-router-dom'
import CollegeLayout from './layouts/CollegeLayout'
import Home from './pages/Home'
import Login from './pages/Login'
import Courses from './pages/Courses'
import MyEnrollments from './pages/MyEnrollments'
import Stats from './pages/Stats'

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Navigate to="/college/A" replace />} />
                <Route path="/college/:collegeId" element={<CollegeLayout />}>
                    <Route index element={<Home />} />
                    <Route path="login" element={<Login />} />
                    <Route path="courses" element={<Courses />} />
                    <Route path="enrollments" element={<MyEnrollments />} />
                </Route>
                <Route path="/integration" element={<Stats />} />
                <Route path="*" element={<Navigate to="/college/A" replace />} />
            </Routes>
        </BrowserRouter>
    )
}
