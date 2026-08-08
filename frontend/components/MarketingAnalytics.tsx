import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Activity, TrendingUp, Users, Zap } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function MarketingAnalytics() {
  const [campaigns, setCampaigns] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch campaign analytics from the backend
  const fetchCampaignAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/analytics`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch analytics: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setCampaigns(data.campaigns || []);
    } catch (err: any) {
      console.error('Error fetching marketing analytics:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchCampaignAnalytics();
  }, []);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Activity className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading analytics...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Activity className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">Error loading analytics</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (campaigns.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Activity className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No campaign data</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <Activity className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">Campaign Performance</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Track marketing campaign effectiveness and ROI
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {campaigns.map((campaign) => (
          <div key={campaign.id || Math.random()} className="bg-card/50 p-4 rounded-lg border border-border/50">
            <div className="mb-3">
              <h3 className="font-semibold text-foreground">{campaign.name}</h3>
              <p className="text-sm text-muted-foreground">{campaign.description}</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-3">
              <div className="text-sm">
                <p className="text-xs font-medium">Impressions:</p>
                <p className="text-xs">{campaign.impressions?.toLocaleString() ?? 'N/A'}</p>
              </div>
              <div className="text-sm">
                <p className="text-xs font-medium">Clicks:</p>
                <p className="text-xs">{campaign.clicks?.toLocaleString() ?? 'N/A'}</p>
              </div>
              <div className="text-sm">
                <p className="text-xs font-medium">CTR:</p>
                <p className="text-xs">{campaign.ctr?.toFixed(2) ?? 'N/A'}%</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-3">
              <div className="text-sm">
                <p className="text-xs font-medium">Conversions:</p>
                <p className="text-xs">{campaign.conversions?.toLocaleString() ?? 'N/A'}</p>
              </div>
              <div className="text-sm">
                <p className="text-xs font-medium">Conversion Rate:</p>
                <p className="text-xs">{campaign.conversionRate?.toFixed(2) ?? 'N/A'}%</p>
              </div>
              <div className="text-sm">
                <p className="text-xs font-medium">Cost:</p>
                <p className="text-xs">${campaign.cost?.toLocaleString() ?? 'N/A'}</p>
              </div>
            </div>
            <div className="mt-3 p-3 bg-gray-50 rounded">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">ROI:</span>
                <span className="text-lg font-bold">${campaign.roi?.toFixed(2) ?? 'N/A'}</span>
              </div>
              <div className="w-full bg-gray-200 rounded h-2 mt-1">
                <div className="bg-brass-500 h-2 rounded" style={{ width: `${campaign.roi > 0 ? Math.min(campaign.roi * 10, 100) : 0}%` }}></div>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}