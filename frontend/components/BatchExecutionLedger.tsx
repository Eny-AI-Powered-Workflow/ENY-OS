'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Loader2, RotateCcw, ShieldAlert } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { supabase } from '@/lib/supabaseClient';

type BatchResult = {
  id: string;
  cohort_name: string;
  contact_id: string;
  contact_name: string | null;
  email: string | null;
  status: string;
  score: number | null;
  category: string | null;
  error: string | null;
  retry_count: number;
  operating_decision: string;
  failure_class: string | null;
  recovery_owner_id: string | null;
  recovery_status: string;
  created_at: string | null;
};

type BatchSummary = {
  total: number;
  succeeded: number;
  pending: number;
  failed: number;
  exhausted: number;
  held?: number;
  escalated?: number;
  rerun_approved?: number;
};

export default function BatchExecutionLedger() {
  const [results, setResults] = useState<BatchResult[]>([]);
  const [summary, setSummary] = useState<BatchSummary>({ total: 0, succeeded: 0, pending: 0, failed: 0, exhausted: 0 });
  const [loading, setLoading] = useState(true);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [decidingId, setDecidingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const getHeaders = async (): Promise<HeadersInit> => {
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token
      ? { 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}` }
      : { 'Content-Type': 'application/json' };
  };

  const loadResults = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/batch-results?limit=30`, {
        headers: await getHeaders(),
        credentials: 'include',
      });
      if (!res.ok) throw new Error(`Failed to load batch results: ${res.status}`);
      const data = await res.json();
      setResults(data.results || []);
      setSummary(data.summary || { total: 0, succeeded: 0, pending: 0, failed: 0, exhausted: 0 });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load batch results');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadResults();
    const interval = setInterval(loadResults, 30_000);
    return () => clearInterval(interval);
  }, []);

  const retry = async (resultId: string) => {
    setRetryingId(resultId);
    setMessage(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/batch-results/${resultId}/retry`, {
        method: 'POST',
        headers: await getHeaders(),
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Retry failed: ${res.status}`);
      setMessage(data.status === 'scored' ? 'Retry completed and the result is back in the queue.' : 'Retry remains pending.');
      await loadResults();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to retry this result');
    } finally {
      setRetryingId(null);
    }
  };

  const decide = async (resultId: string, decision: 'rerun' | 'hold' | 'escalate') => {
    const reason = window.prompt(`Reason for ${decision}:`);
    if (!reason?.trim()) return;
    setDecidingId(resultId);
    setMessage(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/batch-results/${resultId}/decision`, {
        method: 'PATCH',
        headers: await getHeaders(),
        credentials: 'include',
        body: JSON.stringify({ decision, reason: reason.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Decision failed: ${res.status}`);
      setMessage(`Recovery decision recorded: ${decision}.`);
      await loadResults();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to record the recovery decision');
    } finally {
      setDecidingId(null);
    }
  };

  return (
    <Card className="w-full border-slate-200/80 bg-white shadow-sm">
      <CardHeader className="border-b border-slate-100 pb-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Approved work</p>
            <CardTitle className="mt-1 text-lg text-slate-900">Batch execution ledger</CardTitle>
          </div>
          <span className="text-xs text-slate-500">{results.length} recent results</span>
        </div>
        {message && <p className="mt-3 text-sm text-slate-600">{message}</p>}
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-5">
          {[
            ['Total', summary.total, 'text-slate-700'],
            ['Succeeded', summary.succeeded, 'text-emerald-700'],
            ['Pending', summary.pending, 'text-amber-700'],
            ['Failed', summary.failed, 'text-rose-700'],
            ['Exhausted', summary.exhausted, 'text-slate-700'],
            ['Held', summary.held || 0, 'text-amber-700'],
            ['Escalated', summary.escalated || 0, 'text-rose-700'],
          ].map(([label, value, color]) => (
            <div key={label} className="rounded-md bg-slate-50 px-2 py-1.5">
              <span className="block text-[10px] uppercase tracking-wide text-slate-400">{label}</span>
              <span className={`font-semibold ${color}`}>{value}</span>
            </div>
          ))}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="flex items-center gap-2 p-5 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading execution results...
          </div>
        ) : results.length === 0 ? (
          <div className="p-5 text-sm text-slate-500">No approved batch results have been recorded yet.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {results.map((result) => {
              const recoverable = ['failed', 'held', 'escalated'].includes(result.status);
              const pendingRetry = result.status === 'failed' && result.operating_decision === 'rerun';
              return (
                <div key={result.id} className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {result.status === 'scored' ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-rose-600" />
                      )}
                      <span className="font-medium text-slate-900">{result.contact_name || result.contact_id}</span>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-600">
                        {result.status}
                      </span>
                      {result.score !== null && <span className="text-xs text-slate-500">Score {result.score}</span>}
                      {recoverable && <span className="inline-flex items-center gap-1 text-xs text-slate-500"><ShieldAlert className="h-3.5 w-3.5" /> {result.failure_class || 'unknown'} · {result.operating_decision}</span>}
                    </div>
                    <p className="mt-1 truncate text-xs text-slate-500">{result.cohort_name} · {result.email || result.contact_id}</p>
                    {result.error && <p className="mt-1 text-xs text-rose-600">{result.error}</p>}
                  </div>
                  {recoverable && <div className="flex shrink-0 flex-wrap justify-end gap-2">
                    {pendingRetry && <button type="button" onClick={() => retry(result.id)} disabled={retryingId === result.id} title="Run the approved retry" className="inline-flex items-center justify-center gap-2 rounded-md border border-cyan-200 px-3 py-2 text-xs font-semibold text-cyan-700 transition hover:bg-cyan-50 disabled:cursor-not-allowed disabled:opacity-60">{retryingId === result.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}{retryingId === result.id ? 'Running...' : 'Run retry'}</button>}
                    {result.operating_decision !== 'rerun' && <button type="button" onClick={() => void decide(result.id, 'rerun')} disabled={decidingId === result.id} title="Approve this result for rerun" className="rounded-md border border-emerald-200 px-3 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-60">Approve rerun</button>}
                    {result.operating_decision !== 'hold' && <button type="button" onClick={() => void decide(result.id, 'hold')} disabled={decidingId === result.id} title="Place this result on hold" className="rounded-md border border-amber-200 px-3 py-2 text-xs font-semibold text-amber-700 hover:bg-amber-50 disabled:opacity-60">Hold</button>}
                    {result.operating_decision !== 'escalate' && <button type="button" onClick={() => void decide(result.id, 'escalate')} disabled={decidingId === result.id} title="Escalate this result" className="rounded-md border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-60">Escalate</button>}
                  </div>}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
