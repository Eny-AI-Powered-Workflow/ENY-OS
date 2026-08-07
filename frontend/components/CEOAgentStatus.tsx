'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Zap, Activity, Tritron, Bot } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function CEOAgentStatus() {
  const [agentStatus, setAgentStatus] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch agent status from the backend
  const fetchAgentStatus = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ceo/agent-status`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch agent status: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setAgentStatus(data.agents || []);
    } catch (err: any) {
      console.error('Error fetching CEO agent status:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchAgentStatus();
  }, []);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Zap className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading agent status...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Zap className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">Error loading agent status</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (agentStatus.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Zap className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No agents found</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <Zap className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">Agent Status</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Monitor AI agent performance and activity
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {agentStatus.map((agent) => (
          <div key={agent.id || agent.name + Math.random()} className="bg-card/50 p-4 rounded-lg border border-border/50 flex items-center space-x-4">
            <div className="w=10 h=10 bg-brass-500/10 rounded-flex items-center justify-center">
              {agent.type === 'workflow' && <Activity className="h-5 w-5 text-brass-500" />}
              {agent.type === 'agent' && <Bot className="h-5 w-5 text-brass-500" />}
              {agent.type === 'analysis' && <Tritron className="h-5 w-5 text-brass-500" />}
              {agent.type === 'notification' && <Zap className="h-5 w-5 text-brass-500" />}
              {/* Default to zap icon */}
              {!['workflow', 'agent', 'analysis', 'notification'].includes(agent.type || '') && (
                <Zap className="h-5 w-5 text-brass-500" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex justify-between">
                <h3 className="font-semibold text-foreground">{agent.name}</h3>
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  agent.status === 'success' ? 'bg-green-100 text-green-800' :
                  agent.status === 'error' ? 'bg-red-100 text-red-800' :
                  agent.status === 'running' ? 'bg-blue-100 text-blue-800' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {agent.status}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">{agent.description}</p>
              {
                "": "",
                "": ""
              }
              <p className="text-xs text-muted-foreground mt-1">
                Last run: {agent.lastRun} •
                <span className="text-brass-500">{agent.runsToday} runs today</span>
              }
            </div>
          })
        )}
      </CardContent>
    </Card>
  );
}