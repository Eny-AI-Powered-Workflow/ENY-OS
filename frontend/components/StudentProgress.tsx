'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { GraduationCap } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

type StudentProgressData = {
  activeStudents: number | null
  programSheetMatches: number | null
  attendanceReported: number | null
  assignmentsReported: number | null
  capstonesReported: number | null
}

export default function StudentProgress({ offerId }: { offerId: string }) {
  const [progressData, setProgressData] = useState({
    activeStudents: null,
    programSheetMatches: null,
    attendanceReported: null,
    assignmentsReported: null,
    capstonesReported: null,
  } as StudentProgressData);
  const [programSheetStatus, setProgramSheetStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProgressData = async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const params = new URLSearchParams({ offer_id: offerId });
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/progress?${params}`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        if (res.status === 401) {
          setError('Your session has expired. Please log in again.');
        } else if (res.status === 503 && payload?.detail?.code === 'provider_not_configured') {
          setError('Kajabi is not configured in the backend environment.');
        } else if (res.status === 403) {
          setError('You do not have permission to view student progress.');
        } else {
          throw new Error(`Failed to fetch progress: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setProgressData(data.progress || {
        activeStudents: null,
        programSheetMatches: null,
        attendanceReported: null,
        assignmentsReported: null,
        capstonesReported: null,
      });
      setProgramSheetStatus(data.sources?.program_sheet ?? null);
    } catch (err: any) {
      console.error('Error fetching student progress:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchProgressData();
  }, [offerId]);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <GraduationCap className="h-5 w-5 text-muted-foreground mr-2" />
          <div className="text-sm">Loading progress data...</div>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <GraduationCap className="h-5 w-5 text-destructive mr-2" />
          <div className="text-sm text-destructive">Student progress unavailable</div>
          <p className="text-center text-sm text-muted-foreground">{error}</p>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <GraduationCap className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">Program Sheet coverage</h2>
        </div>
        <p className="text-xs text-muted-foreground">Counts indicate populated source fields, not grades or risk decisions.</p>
      </CardHeader>
      <CardContent className="space-y-6">
        <p className="text-xs text-muted-foreground">Program Sheet source: {programSheetStatus?.replaceAll('_', ' ') || 'Unknown'}</p>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          {[
            ['Active learners', progressData.activeStudents],
            ['Matched Program Sheet rows', progressData.programSheetMatches],
            ['Attendance values', progressData.attendanceReported],
            ['Assignment values', progressData.assignmentsReported],
            ['Capstone values', progressData.capstonesReported],
          ].map(([label, value]) => (
            <div key={String(label)} className="border border-slate-200 p-4">
              <dt className="text-sm text-muted-foreground">{label}</dt>
              <dd className="mt-2 text-xl font-semibold text-foreground">{typeof value === 'number' ? value.toLocaleString() : 'Unavailable'}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
