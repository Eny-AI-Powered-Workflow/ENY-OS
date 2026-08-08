'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Users, Search, Trash2 } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function EnrollmentLeads() {
  const [leads, setLeads] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchLeads = async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const query = encodeURIComponent(searchTerm);
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/leads?limit=20&search=${query}`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch leads: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setLeads(data.leads || []);
    } catch (err: any) {
      console.error('Error fetching enrollment leads:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [searchTerm]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Users className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading leads...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Users className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">Error loading leads</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (leads.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Users className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No leads found</CardTitle>
        </CardHeader>
        {searchTerm && (
          <p className="text-center text-sm text-muted-foreground py-4">
            No leads match "{searchTerm}"
          </p>
        )}
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center">
            <Users className="h-4 w-4 mr-2" />
            <h2 className="text-xl font-semibold">Leads</h2>
          </div>
          <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search leads..."
                value={searchTerm}
                onChange={handleSearchChange}
                className="border rounded px-3 py-1.5 pl-9 text-sm focus:outline-none focus:ring-2 focus:ring-brass-500"
              />
            </div>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Manage and nurture leads through the enrollment pipeline
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {leads.map((lead) => (
          <div key={lead.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center mb-2">
                  <div className="w-8 h-8 bg-brass-500/10 rounded-full flex items-center justify-center">
                    <Users className="h-4 w-4 text-brass-500" />
                  </div>
                  <div className="ml-3">
                    <h3 className="font-semibold text-foreground truncate max-w-xs">
                      {lead.firstName} {lead.lastName}
                    </h3>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground truncate">{lead.email}</p>
                {lead.phone && <p className="text-xs text-muted-foreground">{lead.phone}</p>}
              </div>
              <div className="flex flex-col items-end space-y-3">
                <div className="text-xs text-muted-foreground">
                  Score: {lead.score || 'N/A'}
                </div>
                <div className="flex flex-wrap gap-2 justify-end">
                  {lead.tags?.map((tag: string, index: number) => (
                    <span
                      key={`${lead.id}-${tag}-${index}`}
                      className={`px-2 py-0.5 text-xs rounded-full ${
                        tag.toLowerCase().includes('hot')
                          ? 'bg-red-100 text-red-800'
                          : tag.toLowerCase().includes('follow')
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="flex space-x-2">
                  <button onClick={() => console.log('View lead:', lead.id)} className="px-3 py-1 text-xs bg-brass-500/10 hover:bg-brass-500/20 rounded">
                    View
                  </button>
                  <button onClick={() => console.log('Delete lead:', lead.id)} className="px-3 py-1 text-xs text-destructive bg-transparent hover:bg-destructive/10 rounded">
                    <Trash2 className="h-3.5 w-3.5 inline-block mr-1" /> Delete
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
