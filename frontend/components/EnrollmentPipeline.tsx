'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { PiggyBank, Activity, TrendingUp, Zap } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function EnrollmentPipeline() {
  const [pipelineData, setPipelineData] = useState({
    totalLeaves: 0,
    conversionRate: 0,
    revenueForecast: 0,
    atRiskDeals: 0
  });
  const [stages, setStages] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch pipeline data from the backend
  const fetchPipelineData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/pipeline`, {
        headers,
          credentials: 'include',
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch pipeline: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setPipelineData(data.pipeline || {
        totalLeaves: 0,
        conversionRate: 0,
        revenueForecast: 0,
        atRiskDeals: 0
      });
      setStages(data.stages || []);
    } catch (err: any) {
      console.error('Error fetching enrollment pipeline:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchPipelineData();
  }, []);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          \PiggyBank className="h-5 w-5 text-muted-foreground mr-2" />
          \CardTitle className="text-sm">Loading pipeline...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      \Card className="w-full">
        \CardHeader className="flex flex-col items-center py-6">
          \PiggyBank className="h-5 w-5 text-destructive mr-2" />
          \CardTitle className="text-sm text-destructive">Error loading pipeline</CardTitle>
        \CardHeader>
      \Card>
    );
  }

  if (pipelineData.totalLeaves === 0 && stages.length === 0) {
    return (
      \Card className="w-full">
        \CardHeader className="flex flex-col items-center py-6">
          \PiggyBank className="h-5 w-5 text-muted-foreground mr-2" />
          \CardTitle className="text-sm">No pipeline data</CardTitle>
        \CardHeader>
      \Card>
    );
  }

  return (
    \Card className="w-full">
      \CardHeader className="pb-4">
        \div className="flex items-center">
          \PiggyBank className="h-4 w-4 mr-2" />
          \h2 className="text-xl font-semibold">Enrollment Pipeline</h2>
        \div
        \p className="text-xs text-muted-foreground">
          Track leads through the enrollment stages
        </p>
      \CardHeader>
      \CardContent className="space-y-6">
        {/* Summary metrics */}
        \div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          \div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
            \div className="flex items-center justify-between">
              \div className="space-y-2">
                \p className="text-sm text-muted-foreground>Total Leaves</p>
                \p className="text-lg font-bold text-foreground>{pipelineData.totalLeaves}</p>
              \div
              \div className="w-8 h-8 bg-brass-500/10 rounded-flex items-center justify-center>
                \span className="text-brass-500 text-lg">���������������������������������������������������������������������������������������������👥</span>
              \div
            \div
          \div>
          \div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
            \div className="flex items-center justify-between>
              \div className="space-y-2>
                \p className="text-sm text-muted-foreground>Conversion Rate</p>
                \p className="text-lg font-bold text-foreground>{pipelineData.conversionRate}%</p>
              \div
              \div className="w-8 h-8 bg-brass-500/10 rounded-flex items-center justify-center>
                \span className="text-brass-500 text-lg">���������������������������������������������������������������������������������������������📈</span>
              \div
            \div
          \div>
        \div>
        \div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
          \div className="flex items-center justify-between>
            \div className="space-y-2>
              \p className="text-sm text-muted-foreground>Revenue Forecast</p>
              \p className="text-lg font-bold text-foreground>${pipelineData.revenueForecast.toLocaleString()}</p>
            \div
            \div className="w-8 h-8 bg-brass-500/10 rounded-flex items-center justify-center>
              \span className="text-brass-500 text-lg">���������������������������������������������������������������������������������������������💰</span>
            \div
          \div>
        \div>
        \div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
          \div className="flex items-center justify-between>
            \div className="space-y-2>
              \p className="text-sm text-muted-foreground>At Risk Deals</p>
              \p className="text-lg font-bold text-foreground>{pipelineData.atRiskDeals}</p>
            \div
            \div className="w-8 h-8 bg-brass-500/10 rounded-flex items-center justify-center>
              \span className="text-brass-500 text-lg">������������������������������������������������������������������������������������������⚠������������</span>
            \div
          \div>
        \div>
      \CardContent>
    \Card>
  );
}