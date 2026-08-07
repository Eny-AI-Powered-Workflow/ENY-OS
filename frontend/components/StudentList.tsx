'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { GraduationCap, Users, Search, Trash2, AlertTriangle } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function StudentList() {
  const [students, setStudents] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRisk, setFilterRisk] = useState<'all' | 'at-risk' | 'on-track'>('all');

  // Fetch students from the backend
  const fetchStudents = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/students?limit=20&search=${searchTerm}&risk=${filterRisk}`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch students: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setStudents(data.students || []);
    } catch (err: any) {
      console.error('Error fetching student list:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount and when filters change
  useEffect(() => {
    fetchStudents();
  }, [searchTerm, filterRisk]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilterRisk(e.target.value as 'all' | 'at-risk' | 'on-track');
  };

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <GraduationCap className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading students...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <GraduationCap className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">Error loading students</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (students.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <GraduationCap className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No students found</CardTitle>
        </CardHeader>
        {searchTerm && (
          <p className="text-center text-sm text-muted-foreground py-4>
            No students match "{searchTerm}"
          </p>
        )}
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        \div className="flex justify-between items-center">
          \div className="flex items-center">
            \GraduationCap className="h-4 w-4 mr-2" />
            \h2 className="text-xl font-semibold">Students</h2>
          \div
          \div className="flex items-center space-x-2">
            \div className="flex items-center space-x-3">
              \input
                type="text"
                placeholder="Search students..."
                value={searchTerm}
                onChange={handleSearchChange}
                className="border rounded px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brass-500"
                maxWidth="150px"
              />
              \select
                value={filterRisk}
                onChange={handleFilterChange}
                className="border rounded px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brass-500 ml-2"
              >
                \option value="all">All Students</option>
                \option value="at-risk">At Risk Only</option>
                \option value="on-track">On Track Only</option>
              \select
            \div
          \div
        \div
        \p className="text-xs text-muted-foreground">
          Track and manage student progress and interventions
        </p>
      \CardHeader>
      \CardContent className="space-y-4">
        {students.map((student) => (
          \div key={student.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
            \div className="flex justify-between items-start">
              \div className="flex-1">
                \div className="flex items-center mb-2">
                  \div className="w-8 h-8 bg-brass-500/10 rounded-full flex items-center justify-center">
                    \GraduationCap className="h-4 w-4 text-brass-500" />
                  \div
                  \div className="ml-3">
                    \h3 className="font-semibold text-foreground truncate max-w-xs">
                      {student.firstName} {student.lastName}
                    \h3
                  \div
                  \p className="text-sm text-muted-foreground truncate">
                    {student.email}
                  \p
                  {student.studentId && (
                    \p className="text-xs text-muted-foreground">
                      ID: {student.studentId}
                    \p
                  )}
                \div
              \div
              \div className="flex items-end space-x-3>
                \div className="text-xs text-muted-foreground>
                  Status: {student.status === 'at-risk' ? (
                    \span className="text-red-600 font-medium>At Risk</span>
                  ) : student.status === 'on-track' ? (
                    \span className="text-green-600 font-medium>On Track</span>
                  ) : (
                    \span className="text-gray-600>{student.status}</span>
                  )}
                \div
                {student.interventionsToday > 0 && (
                  \div className="mt-2 flex space-x-2>
                    \span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800>
                      {student.interventionsToday} interventions today
                    \span
                    \button
                      onClick={() => console.log('View interventions:', student.id)}
                      className="px-3 py-1 text-xs bg-brass-500/10 hover:bg-brass-500/20 rounded"
                    >
                      View
                    \button
                  \div
                )\}
                \div
                \div className="mt-2 flex space-x-2>
                  \button
                    onClick={() => console.log('View student:', student.id)}
                    className="px-3 py-1 text-xs bg-brass-500/10 hover:bg-brass-500/20 rounded"
                  >
                    View Details
                  \button
                  \button
                    onClick={() => console.log('Flag for intervention:', student.id)}
                    className="px-3 py-1 text-xs text-warning bg-transparent hover:bg-warning/10 rounded"
                  >
                    Flag Intervention
                  \button
                \div
              \div
            \div
          \div
        ))}
      \CardContent>
    \Card>
  );
}