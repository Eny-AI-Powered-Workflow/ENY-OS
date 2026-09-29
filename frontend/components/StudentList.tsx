'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { GraduationCap, Search } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

type Student = {
  id: string
  name: string
  email: string | null
  external_user_id: string | null
  offer_title: string
  offer_status: string
  program_sheet_status: string
  program: string | null
  cohort: string | null
  attendance: string | null
  assignment_status: string | null
  capstone_status: string | null
}

export default function StudentList({ offerId }: { offerId: string }) {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const fetchStudents = async (requestedPage: number, append = false) => {
    try {
      setLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const params = new URLSearchParams({ offer_id: offerId, limit: '25', page: String(requestedPage) });
      if (searchTerm) params.set('search', searchTerm);
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/students?${params}`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        if (res.status === 401) {
          setError('Your session has expired. Please log in again.');
        } else if (res.status === 503 && payload?.detail?.code === 'provider_not_configured') {
          setError('Kajabi is not configured in the backend environment.');
        } else if (res.status === 503 && payload?.detail?.code === 'source_not_configured') {
          setError('Student records are unavailable until the approved source is connected.');
        } else if (res.status === 403) {
          setError('You do not have permission to view student records.');
        } else {
          throw new Error(`Failed to fetch students: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setStudents((current) => append ? [...current, ...(data.students || [])] : (data.students || []));
      setPage(data.page ?? requestedPage);
      setHasMore(Boolean(data.has_more));
    } catch (err: any) {
      console.error('Error fetching student list:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setStudents([]);
    setPage(1);
    void fetchStudents(1);
  }, [offerId, searchTerm]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
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
          <CardTitle className="text-sm text-destructive">Student records unavailable</CardTitle>
          <p className="text-center text-sm text-muted-foreground">{error}</p>
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
          <p className="text-center text-sm text-muted-foreground py-4">
            No students match "{searchTerm}"
          </p>
        )}
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center">
            <GraduationCap className="h-4 w-4 mr-2" />
            <h2 className="text-xl font-semibold">Students</h2>
          </div>
          <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search students..."
                value={searchTerm}
                onChange={handleSearchChange}
                className="border rounded px-3 py-1.5 pl-9 text-sm focus:outline-none focus:ring-2 focus:ring-brass-500"
              />
            </div>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">Current Kajabi offer grants joined to matching Program Sheet fields.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {students.map((student) => (
          <div key={student.id} className="border rounded-lg p-4">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center mb-2">
                  <div className="w-8 h-8 bg-brass-500/10 rounded-full flex items-center justify-center">
                    <GraduationCap className="h-4 w-4 text-brass-500" />
                  </div>
                  <div className="ml-3">
                    <h3 className="font-semibold text-foreground truncate max-w-xs">{student.name}</h3>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground truncate">{student.email}</p>
                {student.external_user_id && <p className="text-xs text-muted-foreground">External ID: {student.external_user_id}</p>}
              </div>
              <div className="grid gap-2 text-right text-xs text-slate-600">
                <span>Offer: {student.offer_status}</span>
                <span>Program Sheet: {student.program_sheet_status.replaceAll('_', ' ')}</span>
              </div>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-slate-100 pt-3 text-sm sm:grid-cols-4">
              <div><dt className="text-xs text-muted-foreground">Program</dt><dd>{student.program || 'Not recorded'}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Cohort</dt><dd>{student.cohort || 'Not recorded'}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Attendance</dt><dd>{student.attendance || 'Not recorded'}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Assignments</dt><dd>{student.assignment_status || 'Not recorded'}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Capstone</dt><dd>{student.capstone_status || 'Not recorded'}</dd></div>
            </dl>
          </div>
        ))}
        {hasMore && (
          <button type="button" disabled={loading} onClick={() => void fetchStudents(page + 1, true)} className="border border-slate-300 px-3 py-2 text-sm text-slate-700 disabled:opacity-50">
            {loading ? 'Loading...' : 'Load more'}
          </button>
        )}
      </CardContent>
    </Card>
  );
}
