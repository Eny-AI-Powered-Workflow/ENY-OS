'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { GraduationCap, Activity, Zap, TrendingUp } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function StudentProgress() {
  const [progressData, setProgressData] = useState({
    graduationRate: 0,
    averageGpa: 0,
    retentionRate: 0,
    collegeAcceptanceRate: 0
  });
  const [interventions, setInterventions] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch progress data from the backend
  const fetchProgressData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/progress`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch progress: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setProgressData(data.progress || {
        graduationRate: 0,
        averageGpa: 0,
        retentionRate: 0,
        collegeAcceptanceRate: 0
      });
      setInterventions(data.recentInterventions || []);
    } catch (err: any) {
      console.error('Error fetching student progress:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchProgressData();
  }, []);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <GraduationCap className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading progress data...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex-func col items-center py-6">
          <GraduationCap className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">Error loading progress data</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (progressData.graduationRate === 0 && interventions.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <GraduationCap className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No progress data available</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <GraduationCap className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">Student Progress & Outcomes</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Track key metrics and recent interventions
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Graduation Rate</p>
                <p className="text-lg font-bold text-foreground>{progressData.graduationRate}%</p>
              </div>
              <div className="w-8 h-8 bg-brass-500/10 rounded-flex items-center justify-center">
                <span className="text-brass-500 text-lg">���������������������������������������������������������������������������������������������🎓</span>
              </div>
            </div>
          </div>
          <div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
            <div className="flex items-center justify-between">
              {""}
            }
          </div>
        </div>
      </CardContent>
    </Card>
  );
}