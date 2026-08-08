'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Activity, Clock, CheckCircle2, Zap } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function RecentTasks() {
  const [tasks, setTasks] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRecentTasks = async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/operations/recent-tasks`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch recent tasks: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setTasks(data.tasks || []);
    } catch (err: any) {
      console.error('Error fetching recent tasks:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentTasks();
  }, []);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Activity className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading recent tasks...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Activity className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">Error loading tasks</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (tasks.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Activity className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No recent tasks</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <Activity className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">Recent Tasks</h2>
        </div>
        <p className="text-xs text-muted-foreground">Latest system and workflow activities</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {tasks.map((task) => (
          <div key={task.id || task.title} className="bg-card/50 p-4 rounded-lg border border-border/50 flex items-center space-x-4">
            <div className="w-10 h-10 bg-brass-500/10 rounded-full flex items-center justify-center">
              {task.type === 'workflow' && <Activity className="h-5 w-5 text-brass-500" />}
              {task.type === 'approval' && <Clock className="h-5 w-5 text-brass-500" />}
              {task.type === 'notification' && <Zap className="h-5 w-5 text-brass-500" />}
              {task.type === 'completed' && <CheckCircle2 className="h-5 w-5 text-brass-500" />}
              {!['workflow', 'approval', 'notification', 'completed'].includes(task.type || '') && <Activity className="h-5 w-5 text-brass-500" />}
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-foreground">{task.title}</h3>
              <p className="text-sm text-muted-foreground">{task.description}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {task.timeAgo} •
                <span className="text-brass-500"> {task.status}</span>
              </p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
