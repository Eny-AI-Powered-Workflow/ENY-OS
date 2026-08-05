'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { AlertTriangle, Clock, Users } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { supabase } from '@/lib/supabaseClient';

interface Lead {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string | null;
  tags: string[];
  score?: number; // optional, if available from backend
}

/**
 * Hot Leads Card component
 * Displays leads that have been scored by the ENY-SALES-SCORE workflow
 */
export default function HotLeadsCard() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch leads from the backend
  const fetchLeads = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/leads?limit=20`, {
        headers,
        credentials: 'include', // also send cookies (for supabase cookie auth)
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch leads: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      // The API returns { leads: Lead[], total, limit, offset }
      const fetchedLeads: Lead[] = data.leads || [];
      setLeads(fetchedLeads);
    } catch (err: any) {
      console.error('Error fetching hot leads:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount and every 30 seconds
  useEffect(() => {
    fetchLeads();
    const interval = setInterval(fetchLeads, 30_000); // 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Clock className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading hot leads...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <AlertTriangle className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">{error}</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (leads.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Users className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No hot leads found</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex flex-col items-center">
          <div className="flex items-center mb-2">
            <Users className="h-4 w-4 mr-2" />
            <h2 className="text-xl font-semibold">Hot Leads</h2>
          </div>
          <p className="text-xs text-muted-foreground">
            Leads scored by the ENY-SALES-SCORE workflow
          </p>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {leads.map((lead) => (
          <div key={lead.id} className="border rounded-lg p-3 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center mb-1">
                  <span className="font-medium">{lead.firstName} {lead.lastName}</span>
                  {lead.score !== undefined && (
                    <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-primary/20 text-primary">
                      Score: {lead.score}
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground truncate max-w-xs">
                  {lead.email}
                </p>
                {lead.phone && (
                  <p className="text-xs text-muted-foreground truncate">
                    {lead.phone}
                  </p>
                )}
              </div>
              <div className="ml-3 flex items-baseline space-x-2">
                {lead.tags.map((tag, idx) => (
                  <span
                    key={idx}
                    className={`px-2 py-0.5 text-xs rounded-full ${
                      tag.toLowerCase().includes('hot')
                        ? 'bg-red-100 text-red-800'
                        : tag.toLowerCase().includes('follow')
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}