import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Zap, Activity, Users, Bot } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function AgentTemplates() {
  const [templates, setTemplates] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<'all' | 'sales' | 'marketing' | 'operations'>('all');

  // Fetch agent templates from the backend
  const fetchAgentTemplates = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/writer/agent-templates?limit=20&category=${filterCategory}`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch agent templates: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setTemplates(data.templates || []);
    } catch (err: any) {
      console.error('Error fetching agent templates:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount and when filter changes
  useEffect(() => {
    fetchAgentTemplates();
  }, [filterCategory]);

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilterCategory(e.target.value as 'all' | 'sales' | 'marketing' | 'operations');
  };

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Zap className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading agent templates...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Zap className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">Error loading agent templates</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (templates.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Zap className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No agent templates found</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center">
          <Zap className="h-4 w-4 mr-2" />
          <h2 className="text-xl font-semibold">Agent Templates</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Deploy and manage AI agent templates for automation
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {templates.map((template) => (
          <div key={template.id || Math.random()} className="bg-card/50 p-4 rounded-lg border border-border/50">
            <div className="mb-3">
              <h3 className="font-semibold text-foreground">{template.name}</h3>
              <p className="text-sm text-muted-foreground">{template.description}</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-3">
              <div className="text-sm">
                <p className="text-xs font-medium">Category:</p>
                <p className="text-xs">{template.category}</p>
              </div>
              <div className="text-sm">
                <p className="text-xs font-medium">Type:</p>
                <p className="text-xs">{template.type}</p>
              </div>
              <div className="text-sm">
                <p className="text-xs font-medium">Version:</p>
                <p className="text-xs">v{template.version}</p>
              </div>
            </div>
            <div className="mt-3 p-3 bg-gray-50 rounded">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Status:</p>
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  template.status === 'active' ? 'bg-green-100 text-green-800' :
                  template.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                  template.status === 'archived' ? 'bg-gray-100 text-gray-700' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {template.status}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded h-2 mt-1">
                <div className="bg-brass-500 h-2 rounded" style={{ width: `${template.usageCount > 0 ? Math.min(template.usageCount * 5, 100) : 0}%` }}></div>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}