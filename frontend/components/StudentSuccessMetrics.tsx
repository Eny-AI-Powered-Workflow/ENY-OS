'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { GraduationCap, Activity, Users, Zap } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function StudentSuccessMetrics() {
  const [metrics, setMetrics] = useState({
    totalStudents: 0,
    atRiskStudents: 0,
    graduationRate: 0,
    interventionsToday: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch metrics from the backend
  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/metrics`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch metrics: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setMetrics(data.metrics || {
        totalStudents: 0,
        atRiskStudents: 0,
        graduationRate: 0,
        interventionsToday: 0
      });
    } catch (err: any) {
      console.error('Error fetching student success metrics:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-card/50 backdrop-blur-sm rounded-xl p-6 border border-border/50">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Total Students</p>
              <p className="text-2xl font-bold text-muted-foreground">Loading...</p>
            </div>
            <div className="w-12 h-12 bg-brass-500/10 rounded-flex items-center justify-center>
              <span className="text-brass-500 text-xl">���������������������������������������������������������������������������������������������🎓</span>
            </div>
          </div>
        </div>
        <div className="bg-card/50 backdrop-blur-sm rounded-xl p-6 border border-border/50">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">At Risk Students</p>
              <p className="text-2xl font-bold text-muted-foreground">Loading...</p>
            </div>
            <div className="w-12 h-12 bg-brass-500/10 rounded-flex items-center justify-center">
              <span className="text-brass-500 text-xl">������������������������������������������������������������������������������⚠������������������������</span>
            </div>
          </div>
        </div>
        <div className="bg-card/50 backdrop-blur-sm rounded-xl p-6 border border-border/50">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Graduation Rate</p>
              <p className="text-2xl font-bold text-muted-foreground">Loading...</p>
            </div>
            <div className="w-12 h-12 bg-brass-500/10 rounded-flex items-center justify-center">
              <span className="text-brass-500 text-xl">���������������������������������������������������������������������������������������������📈</span>
            </div>
          </div>
        </div>
        <div className="bg-card/50 backdrop-blur-sm rounded-xl p-6 border border-border/50">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Interventions Today</p>
              <p className="text-2xl font-bold text-muted-foreground">Loading...</p>
            </div>
            <div className="w-12 h-12 bg-brass-500/10 rounded-flex items-center justify-center">
              <span className="text-brass-500 text-xl">������������������������������������������������������������������������������⚡</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6>
        <div className="bg-card/50 backdrop-blur-sm rounded-xl p-6 border border-border/50>
          <div className="flex items-center justify-between>
            <div className="space-y-2>
              <p className="text-sm text-muted-foreground\">Total Students</p>
              <p className=\"text-2xl font-bold text-destructive\">Error loading</p>
            </div>
            <div className=\"w-12 h-12 bg-brass-500/10 rounded-flex items-center justify-center\>
              <span className=\"text-brass-500 text-xl\">���������������������������������������������������������������������������������������������🎓</span>
            </div>
          </div>
        </div>
        <div className=\"bg-card/50 backdrop-blur-sm rounded-xl p-6 border border-border/50\>
          <div className=\"flex items-center justify-between\>
            <div className=\"space-y-2\>
              <p className=\"text-sm text-muted-foreground\">At Risk Students</p