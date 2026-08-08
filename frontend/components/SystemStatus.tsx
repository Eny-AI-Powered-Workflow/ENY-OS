'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Server } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function SystemStatus() {
  const [metrics, setMetrics] = useState({
    systemUptime: 0,
    activeWorkflows: 0,
    tasksCompleted: 0,
    avgResponseTime: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/operations/metrics`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch system status: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setMetrics(data.metrics || {
        systemUptime: 0,
        activeWorkflows: 0,
        tasksCompleted: 0,
        avgResponseTime: 0,
      });
    } catch (err: any) {
      console.error('Error fetching system status:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Server className="h-5 w-5 text-muted-foreground mr-2" />
          <div className="text-sm">Loading system status...</div>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Server className="h-5 w-5 text-destructive mr-2" />
          <div className="text-sm text-destructive">Error loading system status</div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <Server className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">System Status</h2>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-card/50 p-3 rounded-lg border border-border/50">
            <p className="text-xs text-muted-foreground">Uptime</p>
            <p className="mt-2 text-lg font-bold text-foreground">{metrics.systemUptime}%</p>
          </div>
          <div className="bg-card/50 p-3 rounded-lg border border-border/50">
            <p className="text-xs text-muted-foreground">Workflows</p>
            <p className="mt-2 text-lg font-bold text-foreground">{metrics.activeWorkflows}</p>
          </div>
          <div className="bg-card/50 p-3 rounded-lg border border-border/50">
            <p className="text-xs text-muted-foreground">Tasks</p>
            <p className="mt-2 text-lg font-bold text-foreground">{metrics.tasksCompleted.toLocaleString()}</p>
          </div>
          <div className="bg-card/50 p-3 rounded-lg border border-border/50">
            <p className="text-xs text-muted-foreground">Avg. Response</p>
            <p className="mt-2 text-lg font-bold text-foreground">{metrics.avgResponseTime} ms</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
