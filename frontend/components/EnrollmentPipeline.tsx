'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { PiggyBank } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

type Pipeline = {
  id: string;
  name: string;
};

type Opportunity = {
  id: string;
  name?: string;
  contactName?: string;
  firstName?: string;
  lastName?: string;
  contactId?: string;
  contact?: {
    name?: string;
    firstName?: string;
    lastName?: string;
  };
  pipelineId?: string;
  pipelineName?: string;
  pipelineStageName?: string;
  stageName?: string;
  status?: string;
  monetaryValue?: number | string;
  expectedValue?: number | string;
};

export default function EnrollmentPipeline() {
  const [pipelineData, setPipelineData] = useState({
    totalLeads: 0,
    conversionRate: 0,
    revenueForecast: 0,
    atRiskDeals: 0,
  });
  const [stages, setStages] = useState<Array<{ id: string; name: string; description: string; count: number; percentage: number }>>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState('all');
  const [pipelineCatalogStatus, setPipelineCatalogStatus] = useState('connected');
  const [maxPagesReached, setMaxPagesReached] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPipelineData = async () => {
    try {
      setLoading(true);
      setError(null);

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
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch pipeline: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      if (data.status === 'error' || data.status === 'not_configured') {
        setError(data.status === 'not_configured'
          ? 'GHL is not configured. Pipeline data is unavailable.'
          : 'GHL pipeline data is unavailable. Please try again later.');
        return;
      }
      setPipelineData(data.pipeline || {
        totalLeads: 0,
        conversionRate: 0,
        revenueForecast: 0,
        atRiskDeals: 0,
      });
      setStages(data.stages || []);
      setPipelines(data.pipelines || []);
      setOpportunities(data.opportunities || []);
      setPipelineCatalogStatus(data.pipeline_catalog_status || 'error');
      setMaxPagesReached(Boolean(data.max_pages_reached));
    } catch (err: any) {
      console.error('Error fetching enrollment pipeline:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipelineData();
  }, []);

  const visibleOpportunities = opportunities.filter((opportunity) =>
    selectedPipelineId === 'all' || opportunity.pipelineId === selectedPipelineId
  );
  const getLeadName = (opportunity: Opportunity) =>
    opportunity.contactName
    || opportunity.contact?.name
    || [opportunity.contact?.firstName || opportunity.firstName, opportunity.contact?.lastName || opportunity.lastName]
      .filter(Boolean)
      .join(' ')
    || opportunity.name
    || 'Unnamed lead';
  const formatPotential = (opportunity: Opportunity) => {
    const rawValue = opportunity.monetaryValue ?? opportunity.expectedValue;
    const value = Number(rawValue);
    return rawValue !== undefined && rawValue !== null && rawValue !== '' && Number.isFinite(value)
      ? new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)
      : 'Not provided';
  };

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <PiggyBank className="h-5 w-5 text-muted-foreground mr-2" />
          <div className="text-sm">Loading pipeline...</div>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <PiggyBank className="h-5 w-5 text-destructive mr-2" />
          <div className="text-sm text-destructive">Error loading pipeline</div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <PiggyBank className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">Enrollment Pipeline</h2>
        </div>
        <p className="text-xs text-muted-foreground">Track leads through the enrollment stages</p>
      </CardHeader>
      <CardContent className="space-y-6">
        <section aria-labelledby="pipeline-opportunities-heading" className="space-y-3">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div>
              <h3 id="pipeline-opportunities-heading" className="font-semibold">Pipeline opportunities</h3>
              <p className="text-xs text-muted-foreground">Live leads and potential value from GoHighLevel</p>
            </div>
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Select pipeline
              <select
                value={selectedPipelineId}
                onChange={(event) => setSelectedPipelineId(event.target.value)}
                className="min-w-48 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
              >
                <option value="all">All pipelines</option>
                {pipelines.map((pipeline) => (
                  <option key={pipeline.id} value={pipeline.id}>{pipeline.name}</option>
                ))}
              </select>
            </label>
          </div>
          {pipelineCatalogStatus !== 'connected' && (
            <p role="status" className="text-sm text-amber-700">
              Pipeline names could not be loaded from GHL. Try refreshing the page.
            </p>
          )}
          {maxPagesReached && (
            <p role="status" className="text-sm text-amber-700">
              Showing the configured maximum number of GHL opportunities. Contact an administrator to increase the inventory limit.
            </p>
          )}
          {visibleOpportunities.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
              No opportunities found for this pipeline.
            </p>
          ) : (
            <ul className="max-h-80 space-y-2 overflow-y-auto">
              {visibleOpportunities.map((opportunity) => (
                <li key={opportunity.id} className="flex flex-col gap-2 rounded-lg border border-border/70 p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">
                      {getLeadName(opportunity)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {opportunity.pipelineStageName || opportunity.stageName || opportunity.status || 'Stage unavailable'}
                    </p>
                  </div>
                  <p className="shrink-0 text-sm font-semibold text-foreground">
                    Potential: {formatPotential(opportunity)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Total Leads</p>
                <p className="text-lg font-bold text-foreground">{pipelineData.totalLeads}</p>
              </div>
              <div className="w-8 h-8 bg-brass-500/10 rounded-full flex items-center justify-center">
                <span className="text-brass-500 text-lg">👥</span>
              </div>
            </div>
          </div>
          <div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Conversion Rate</p>
                <p className="text-lg font-bold text-foreground">{pipelineData.conversionRate}%</p>
              </div>
              <div className="w-8 h-8 bg-brass-500/10 rounded-full flex items-center justify-center">
                <span className="text-brass-500 text-lg">📈</span>
              </div>
            </div>
          </div>
          <div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Revenue Forecast</p>
                <p className="text-lg font-bold text-foreground">${pipelineData.revenueForecast.toLocaleString()}</p>
              </div>
              <div className="w-8 h-8 bg-brass-500/10 rounded-full flex items-center justify-center">
                <span className="text-brass-500 text-lg">💰</span>
              </div>
            </div>
          </div>
          <div className="bg-card/50 backdrop-blur-sm rounded-xl p-4 border border-border/50">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">At Risk Deals</p>
                <p className="text-lg font-bold text-foreground">{pipelineData.atRiskDeals}</p>
              </div>
              <div className="w-8 h-8 bg-brass-500/10 rounded-full flex items-center justify-center">
                <span className="text-brass-500 text-lg">⚠️</span>
              </div>
            </div>
          </div>
        </div>

        {stages.length > 0 && (
          <div className="space-y-3">
            {stages.map((stage) => (
              <div key={stage.id} className="bg-card/50 p-3 rounded-lg border border-border/50">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">{stage.name}</p>
                    <p className="text-xs text-muted-foreground">{stage.description}</p>
                  </div>
                  <span className="text-sm font-semibold">{stage.count}</span>
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded h-2">
                  <div className="bg-brass-500 h-2 rounded" style={{ width: `${stage.percentage}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
