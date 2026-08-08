'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Megaphone } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function CampaignList() {
  const [campaigns, setCampaigns] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCampaigns = async () => {
    try {
      setLoading(true);
      setError(null);

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
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch campaigns: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setCampaigns(data.campaigns || []);
    } catch (err: any) {
      console.error('Error fetching campaigns:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Megaphone className="h-5 w-5 text-muted-foreground mr-2" />
          <div className="text-sm">Loading campaigns...</div>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Megaphone className="h-5 w-5 text-destructive mr-2" />
          <div className="text-sm text-destructive">Error loading campaigns</div>
        </CardHeader>
      </Card>
    );
  }

  if (campaigns.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Megaphone className="h-5 w-5 text-muted-foreground mr-2" />
          <div className="text-sm">No campaign data</div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <Megaphone className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">Campaigns</h2>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {campaigns.map((campaign) => (
          <div key={campaign.id || campaign.name} className="bg-card/50 p-4 rounded-lg border border-border/50">
            <div className="flex justify-between items-start gap-3">
              <div className="flex-1">
                <h3 className="font-semibold text-foreground">{campaign.name}</h3>
                <p className="text-sm text-muted-foreground">{campaign.description}</p>
              </div>
              <span className="text-xs font-medium text-brass-500">{campaign.conversionRate?.toFixed(2) ?? '0.00'}%</span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
              <div>Impressions: {campaign.impressions?.toLocaleString() ?? 'N/A'}</div>
              <div>Clicks: {campaign.clicks?.toLocaleString() ?? 'N/A'}</div>
              <div>CTR: {campaign.ctr?.toFixed(2) ?? '0.00'}%</div>
              <div>ROI: ${campaign.roi?.toFixed(2) ?? '0.00'}</div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
