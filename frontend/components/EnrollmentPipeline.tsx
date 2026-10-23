'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Layers3, PiggyBank, RefreshCw, Users } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

type Pipeline = {
  id: string;
  name: string;
  stages?: Array<{ id: string; name: string }>;
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
  pipelineStageId?: string;
  pipelineName?: string;
  pipelineStageName?: string;
  stageName?: string;
  status?: string;
  monetaryValue?: number | string;
  expectedValue?: number | string;
};

type OpportunityGroup = {
  key: string;
  name: string;
  opportunities: Opportunity[];
};

type CohortGroup = {
  id: string;
  name: string;
  opportunities: Opportunity[];
  stages: OpportunityGroup[];
  potential: number;
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

  const getOpportunityPotential = (opportunity: Opportunity) => {
    const value = Number(opportunity.monetaryValue ?? opportunity.expectedValue);
    return Number.isFinite(value) ? value : 0;
  };

  const cohortGroups = useMemo<CohortGroup[]>(() => {
    const opportunitiesByPipeline = new Map<string, Opportunity[]>();
    for (const opportunity of opportunities) {
      const key = opportunity.pipelineId || 'unassigned';
      const group = opportunitiesByPipeline.get(key) || [];
      group.push(opportunity);
      opportunitiesByPipeline.set(key, group);
    }

    const groups = pipelines.map((pipeline) => {
      const cohortOpportunities = opportunitiesByPipeline.get(pipeline.id) || [];
      const stageNames = new Map((pipeline.stages || []).map((stage) => [stage.id, stage.name]));
      const opportunitiesByStage = new Map<string, OpportunityGroup>();

      for (const opportunity of cohortOpportunities) {
        const stageName = opportunity.pipelineStageName
          || opportunity.stageName
          || stageNames.get(opportunity.pipelineStageId || '')
          || opportunity.status
          || 'Stage unavailable';
        const stageKey = opportunity.pipelineStageId || stageName;
        const group = opportunitiesByStage.get(stageKey) || {
          key: stageKey,
          name: stageName,
          opportunities: [],
        };
        group.opportunities.push(opportunity);
        opportunitiesByStage.set(stageKey, group);
      }

      const pipelineStageOrder = (pipeline.stages || []).map((stage) => stage.id);
      const groupedStages = Array.from(opportunitiesByStage.values()).sort((left, right) => {
        const leftIndex = pipelineStageOrder.indexOf(left.key);
        const rightIndex = pipelineStageOrder.indexOf(right.key);
        if (leftIndex === -1) return rightIndex === -1 ? 0 : 1;
        if (rightIndex === -1) return -1;
        return leftIndex - rightIndex;
      });

      return {
        id: pipeline.id,
        name: pipeline.name,
        opportunities: cohortOpportunities,
        stages: groupedStages,
        potential: cohortOpportunities.reduce((sum, opportunity) => sum + getOpportunityPotential(opportunity), 0),
      };
    });

    const unassigned = opportunitiesByPipeline.get('unassigned') || [];
    if (unassigned.length) {
      groups.push({
        id: 'unassigned',
        name: 'Other opportunities',
        opportunities: unassigned,
        stages: [{
          key: 'unassigned',
          name: 'Pipeline unavailable',
          opportunities: unassigned,
        }],
        potential: unassigned.reduce((sum, opportunity) => sum + getOpportunityPotential(opportunity), 0),
      });
    }

    return selectedPipelineId === 'all'
      ? groups
      : groups.filter((group) => group.id === selectedPipelineId);
  }, [opportunities, pipelines, selectedPipelineId]);

  if (loading) {
    return (
      <Card className="flex h-[min(72vh,760px)] min-h-[520px] w-full flex-col overflow-hidden border-slate-200/80 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
        <CardHeader className="flex shrink-0 flex-col items-center justify-center gap-2 border-b border-slate-100 bg-gradient-to-br from-white via-white to-emerald-50/60 py-6">
          <PiggyBank className="h-5 w-5 text-muted-foreground mr-2" />
          <div className="text-sm">Loading pipeline...</div>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="flex h-[min(72vh,760px)] min-h-[520px] w-full flex-col overflow-hidden border-slate-200/80 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
        <CardContent className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 py-8 text-center">
          <PiggyBank className="h-5 w-5 text-destructive" />
          <div>
            <h2 className="font-semibold text-destructive">Unable to load the enrollment pipeline</h2>
            <p role="alert" className="mt-1 text-sm text-muted-foreground">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => void fetchPipelineData()}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <RefreshCw className="h-4 w-4" />
            Try again
          </button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="flex h-[min(72vh,760px)] min-h-[520px] w-full flex-col overflow-hidden border-slate-200/80 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
      <CardHeader className="shrink-0 border-b border-slate-100 bg-gradient-to-br from-white via-white to-emerald-50/60 px-5 pb-4 pt-5">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-100 bg-emerald-50 text-emerald-700 shadow-sm">
            <PiggyBank className="h-4 w-4" />
          </span>
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-slate-950">Enrollment Pipeline</h2>
            <p className="mt-1 text-xs text-slate-500">Live opportunities, stages, and potential value</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5 pt-4 [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin]">
        <div className="space-y-5">
        <section aria-labelledby="pipeline-opportunities-heading" className="space-y-3">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div>
              <h3 id="pipeline-opportunities-heading" className="text-sm font-semibold text-slate-900">Pipeline opportunities</h3>
              <p className="mt-1 text-xs text-slate-500">Live leads and potential value from GoHighLevel</p>
            </div>
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Select pipeline
              <select
                value={selectedPipelineId}
                onChange={(event) => setSelectedPipelineId(event.target.value)}
                className="min-w-48 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-100"
              >
                <option value="all">All pipelines</option>
                {pipelines.map((pipeline) => (
                  <option key={pipeline.id} value={pipeline.id}>{pipeline.name}</option>
                ))}
              </select>
            </label>
          </div>
          {pipelineCatalogStatus !== 'connected' && (
            <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
              Pipeline names could not be loaded from GHL. Try refreshing the page.
            </p>
          )}
          {maxPagesReached && (
            <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
              Showing the configured maximum number of GHL opportunities. Contact an administrator to increase the inventory limit.
            </p>
          )}
          {cohortGroups.every((cohort) => cohort.opportunities.length === 0) ? (
            <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
              No opportunities found in the selected pipeline.
            </p>
          ) : (
            <div className="space-y-4">
              {cohortGroups.filter((cohort) => cohort.opportunities.length > 0).map((cohort) => (
                <article key={cohort.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                  <header className="flex flex-col gap-4 border-b border-slate-100 bg-gradient-to-r from-violet-50/80 via-white to-emerald-50/60 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-violet-100 bg-violet-100/80 text-violet-700">
                        <Layers3 className="h-5 w-5" aria-hidden="true" />
                      </span>
                      <div className="min-w-0">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-700">GHL pipeline</p>
                        <h4 className="truncate text-base font-semibold text-slate-950">{cohort.name}</h4>
                      </div>
                    </div>
                    <div className="flex items-center gap-5 pl-[52px] sm:pl-0">
                      <div>
                        <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">Leads</p>
                        <p className="mt-0.5 flex items-center gap-1.5 text-sm font-semibold text-slate-800">
                          <Users className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                          {cohort.opportunities.length}
                        </p>
                      </div>
                      <div className="border-l border-slate-200 pl-5">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">Potential</p>
                        <p className="mt-0.5 text-sm font-semibold text-emerald-700">
                          {new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(cohort.potential)}
                        </p>
                      </div>
                    </div>
                  </header>

                  <div className="space-y-4 p-4 sm:p-5">
                    {cohort.stages.map((stage) => (
                      <section key={stage.key} aria-label={`${stage.name} stage`}>
                        <div className="mb-2 flex items-center justify-between gap-3">
                          <h5 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{stage.name}</h5>
                          <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-semibold tabular-nums text-violet-700">
                            {stage.opportunities.length}
                          </span>
                        </div>
                        <ul className="divide-y divide-slate-100 rounded-xl border border-slate-100 bg-white">
                          {stage.opportunities.map((opportunity) => (
                            <li key={opportunity.id} className="flex flex-col gap-2 px-3 py-3 transition-colors hover:bg-slate-50/80 sm:flex-row sm:items-center sm:justify-between sm:px-4">
                              <div className="flex min-w-0 items-center gap-3">
                                <span className="h-2 w-2 shrink-0 rounded-full bg-gradient-to-br from-violet-500 to-indigo-500 shadow-[0_0_0_3px_rgba(139,92,246,0.10)]" aria-hidden="true" />
                                <div className="min-w-0">
                                  <p className="truncate text-sm font-medium text-slate-900">{getLeadName(opportunity)}</p>
                                  {opportunity.status && (
                                    <p className="mt-0.5 text-xs capitalize text-slate-500">{opportunity.status}</p>
                                  )}
                                </div>
                              </div>
                              <p className="pl-5 text-sm font-semibold tabular-nums text-emerald-700 sm:pl-0">
                                {formatPotential(opportunity)}
                              </p>
                            </li>
                          ))}
                        </ul>
                      </section>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200/80 bg-gradient-to-br from-white to-violet-50/60 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-xs font-medium text-slate-500">Total Leads</p>
                <p className="text-xl font-semibold tabular-nums text-slate-900">{pipelineData.totalLeads}</p>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
                <Users className="h-4 w-4" />
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-slate-200/80 bg-gradient-to-br from-white to-sky-50/60 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-xs font-medium text-slate-500">Conversion Rate</p>
                <p className="text-xl font-semibold tabular-nums text-slate-900">{pipelineData.conversionRate}%</p>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-100 text-sky-700">
                <span className="text-sm" aria-hidden="true">↗</span>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-slate-200/80 bg-gradient-to-br from-white to-emerald-50/60 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-xs font-medium text-slate-500">Revenue Forecast</p>
                <p className="text-xl font-semibold tabular-nums text-slate-900">${pipelineData.revenueForecast.toLocaleString()}</p>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                <PiggyBank className="h-4 w-4" />
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-slate-200/80 bg-gradient-to-br from-white to-amber-50/60 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-xs font-medium text-slate-500">At Risk Deals</p>
                <p className="text-xl font-semibold tabular-nums text-slate-900">{pipelineData.atRiskDeals}</p>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
                <span className="text-sm font-bold" aria-hidden="true">!</span>
              </div>
            </div>
          </div>
        </div>

        {stages.length > 0 && (
          <div className="space-y-3">
            {stages.map((stage) => (
              <div key={stage.id} className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-800">{stage.name}</p>
                    <p className="text-xs text-muted-foreground">{stage.description}</p>
                  </div>
                  <span className="text-sm font-semibold">{stage.count}</span>
                </div>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500" style={{ width: `${stage.percentage}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>
      </CardContent>
    </Card>
  );
}
