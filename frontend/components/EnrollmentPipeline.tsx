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
      <Card className="flex h-[min(72vh,760px)] min-h-[520px] w-full flex-col overflow-hidden rounded-2xl border-white/[0.06] bg-[#0d1724] text-slate-100 shadow-[0_18px_50px_rgba(2,6,23,0.24)]">
        <CardHeader className="flex shrink-0 flex-col items-center justify-center gap-2 border-b border-white/[0.06] bg-[#101d2c] py-6">
          <PiggyBank className="mr-2 h-5 w-5 text-emerald-300" />
          <div className="text-sm text-slate-300">Loading pipeline...</div>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="flex h-[min(72vh,760px)] min-h-[520px] w-full flex-col overflow-hidden rounded-2xl border-white/[0.06] bg-[#0d1724] text-slate-100 shadow-[0_18px_50px_rgba(2,6,23,0.24)]">
        <CardContent className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 py-8 text-center">
          <PiggyBank className="h-5 w-5 text-destructive" />
          <div>
            <h2 className="font-semibold text-destructive">Unable to load the enrollment pipeline</h2>
            <p role="alert" className="mt-1 text-sm text-slate-400">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => void fetchPipelineData()}
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-[#172536] px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-[#203149] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <RefreshCw className="h-4 w-4" />
            Try again
          </button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="flex h-[min(72vh,760px)] min-h-[520px] w-full flex-col overflow-hidden rounded-2xl border-white/[0.06] bg-[#0d1724] text-slate-100 shadow-[0_18px_50px_rgba(2,6,23,0.24)]">
      <CardHeader className="shrink-0 border-b border-white/[0.06] bg-gradient-to-br from-[#101d2c] via-[#101b29] to-[#122033] px-4 pb-4 pt-4 sm:px-5 sm:pt-5">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-300/15 bg-emerald-300/[0.08] text-emerald-300 shadow-sm">
            <PiggyBank className="h-4 w-4" />
          </span>
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-slate-100">Enrollment Pipeline</h2>
            <p className="mt-1 text-xs text-slate-400">Live opportunities, stages, and potential value</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 pb-4 pt-3 [scrollbar-color:rgb(71_85_105)_transparent] [scrollbar-width:thin] sm:px-4 sm:pt-4">
        <div className="space-y-4">
        <section aria-labelledby="pipeline-opportunities-heading" className="space-y-3">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div>
              <h3 id="pipeline-opportunities-heading" className="text-sm font-semibold text-slate-100">Pipeline opportunities</h3>
              <p className="mt-1 text-xs text-slate-400">Live leads and potential value from GoHighLevel</p>
            </div>
            <label className="flex flex-col gap-1 text-xs text-slate-400">
              Select pipeline
              <select
                value={selectedPipelineId}
                onChange={(event) => setSelectedPipelineId(event.target.value)}
                className="min-w-48 rounded-xl border border-white/[0.07] bg-[#0a1320] px-3 py-2 text-sm text-slate-100 shadow-sm focus:border-cyan-400/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/10"
              >
                <option value="all">All pipelines</option>
                {pipelines.map((pipeline) => (
                  <option key={pipeline.id} value={pipeline.id}>{pipeline.name}</option>
                ))}
              </select>
            </label>
          </div>
          {pipelineCatalogStatus !== 'connected' && (
            <p role="status" className="rounded-xl border border-amber-400/20 bg-amber-400/[0.08] px-3 py-2 text-xs leading-5 text-amber-200">
              Pipeline names could not be loaded from GHL. Try refreshing the page.
            </p>
          )}
          {maxPagesReached && (
            <p role="status" className="rounded-xl border border-amber-400/20 bg-amber-400/[0.08] px-3 py-2 text-xs leading-5 text-amber-200">
              Showing the configured maximum number of GHL opportunities. Contact an administrator to increase the inventory limit.
            </p>
          )}
          {cohortGroups.every((cohort) => cohort.opportunities.length === 0) ? (
            <p className="rounded-xl border border-dashed border-slate-700 bg-[#101b29] p-5 text-sm text-slate-400">
              No opportunities found in the selected pipeline.
            </p>
          ) : (
            <div className="space-y-4">
              {cohortGroups.filter((cohort) => cohort.opportunities.length > 0).map((cohort) => (
                <article key={cohort.id} className="overflow-hidden rounded-2xl border border-white/[0.06] bg-[#111d2b] shadow-sm">
                  <header className="flex flex-col gap-3 border-b border-white/[0.06] bg-gradient-to-r from-[#172338] via-[#121e2c] to-[#10251f] p-3 sm:flex-row sm:items-center sm:justify-between sm:px-4">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-violet-300/15 bg-violet-300/[0.08] text-violet-200">
                        <Layers3 className="h-5 w-5" aria-hidden="true" />
                      </span>
                      <div className="min-w-0">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-300">GHL pipeline</p>
                        <h4 className="truncate text-sm font-semibold text-slate-100">{cohort.name}</h4>
                      </div>
                    </div>
                    <div className="flex items-center gap-5 pl-[52px] sm:pl-0">
                      <div>
                        <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">Leads</p>
                        <p className="mt-0.5 flex items-center gap-1.5 text-sm font-semibold text-slate-200">
                          <Users className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                          {cohort.opportunities.length}
                        </p>
                      </div>
                      <div className="border-l border-white/10 pl-5">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">Potential</p>
                        <p className="mt-0.5 text-sm font-semibold text-emerald-300">
                          {new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(cohort.potential)}
                        </p>
                      </div>
                    </div>
                  </header>

                  <div className="space-y-4 p-4 sm:p-5">
                    {cohort.stages.map((stage) => (
                      <section key={stage.key} aria-label={`${stage.name} stage`}>
                        <div className="mb-2 flex items-center justify-between gap-3">
                          <h5 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{stage.name}</h5>
                          <span className="rounded-md bg-violet-400/10 px-2 py-1 text-[10px] font-semibold tabular-nums text-violet-200">
                            {stage.opportunities.length}
                          </span>
                        </div>
                        <ul className="divide-y divide-white/[0.05] rounded-xl border border-white/[0.05] bg-[#0b1420]">
                          {stage.opportunities.map((opportunity) => (
                            <li key={opportunity.id} className="flex flex-col gap-2 px-3 py-3 transition-colors hover:bg-white/[0.03] sm:flex-row sm:items-center sm:justify-between sm:px-3">
                              <div className="flex min-w-0 items-center gap-3">
                                <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-400 shadow-[0_0_0_3px_rgba(52,211,153,0.10)]" aria-hidden="true" />
                                <div className="min-w-0">
                                  <p className="truncate text-xs font-medium text-slate-100">{getLeadName(opportunity)}</p>
                                  {opportunity.status && (
                                    <p className="mt-0.5 text-[10px] capitalize text-slate-400">{opportunity.status}</p>
                                  )}
                                </div>
                              </div>
                              <p className="pl-5 text-xs font-semibold tabular-nums text-emerald-300 sm:pl-0">
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
          <div className="rounded-xl border border-white/[0.06] bg-[#111d2b] p-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-[10px] font-medium text-slate-400">Total Leads</p>
                <p className="text-lg font-semibold tabular-nums text-slate-100">{pipelineData.totalLeads}</p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-400/10 text-violet-300">
                <Users className="h-4 w-4" />
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111d2b] p-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-[10px] font-medium text-slate-400">Conversion Rate</p>
                <p className="text-lg font-semibold tabular-nums text-slate-100">{pipelineData.conversionRate}%</p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-400/10 text-cyan-300">
                <span className="text-sm" aria-hidden="true">↗</span>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111d2b] p-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-[10px] font-medium text-slate-400">Revenue Forecast</p>
                <p className="text-lg font-semibold tabular-nums text-slate-100">${pipelineData.revenueForecast.toLocaleString()}</p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-400/10 text-emerald-300">
                <PiggyBank className="h-4 w-4" />
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111d2b] p-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-[10px] font-medium text-slate-400">At Risk Deals</p>
                <p className="text-lg font-semibold tabular-nums text-slate-100">{pipelineData.atRiskDeals}</p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-400/10 text-amber-300">
                <span className="text-sm font-bold" aria-hidden="true">!</span>
              </div>
            </div>
          </div>
        </div>

        {stages.length > 0 && (
          <div className="space-y-3">
            {stages.map((stage) => (
              <div key={stage.id} className="rounded-xl border border-white/[0.06] bg-[#111d2b] p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-100">{stage.name}</p>
                    <p className="text-xs text-slate-400">{stage.description}</p>
                  </div>
                  <span className="text-sm font-semibold">{stage.count}</span>
                </div>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[#26364a]">
                  <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400" style={{ width: `${stage.percentage}%` }}></div>
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
