import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Activity, Clock, Users, Zap } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function CEOHeatmap() {
  const [recentActivity, setRecentActivity] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch recent activity from the backend
  const fetchRecentActivity = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ceo/recent-activity`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch recent activity: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setRecentActivity(data.activities || []);
    } catch (err: any) {
      console.error('Error fetching CEO recent activity:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchRecentActivity();
  }, []);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Activity className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading recent activity...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Activity className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">Error loading activity</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (recentActivity.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Activity className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No recent activity</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <Activity className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">Recent Activity</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Latest actions across the platform
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {recentActivity.map((activity) => (
          <div key={activity.id || Math.random()} className="bg-card/50 p-4 rounded-lg border border-border/50 flex items-center space-x-4">
            <div className="w-10 h-10 bg-brass-500/10 rounded-flex items-center justify-center">
              {activity.icon === 'users' && <Users className="h-5 w-5 text-brass-500" />}
              {activity.icon === 'clock' && <Clock className="h-5 w-5 text-brass-500" />}
              {activity.icon === 'activity' && <Activity className="h-5 w-5 text-brass-500" />}
              {activity.icon === 'zap' && <Zap className="h-5 w-5 text-brass-500" />}
              {/* Default to activity icon */}
              {!['users', 'clock', 'activity', 'zap'].includes(activity.icon || '') && (
                <Activity className="h-5 w-5 text-brass-500" />
              )}
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-foreground">{activity.title}</h3>
              <p className="text-sm text-muted-foreground">{activity.description}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {activity.timeAgo} •
                <span className="text-brass-500">{activity.action}</span>
              </p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}