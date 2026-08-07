import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Pencil, Activity, Search, Trash2, CheckCircle2 } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

export default function DocumentList() {
  const [documents, setDocuments] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'sop' | 'template' | 'report'>('all');

  // Fetch documents from the backend
  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get session to attach auth header if needed
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/writer/documents?limit=20&search=${searchTerm}&type=${filterType}`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        // If we get a 401 or 403, maybe session expired
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch documents: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (err: any) {
      console.error('Error fetching document list:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount and when filters change
  useEffect(() => {
    fetchDocuments();
  }, [searchTerm, filterType]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilterType(e.target.value as 'all' | 'sop' | 'template' | 'report');
  };

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Pencil className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading documents...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Pencil className="h-5 w-5 text-destructive mr-2" />
          <CardTitle className="text-sm text-destructive">Error loading documents</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (documents.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <Pencil className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">No documents found</CardTitle>
        </CardHeader>
        {searchTerm && (
          <p className="text-center text-sm text-muted-foreground py-4">
            No documents match "{searchTerm}"
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
            <Pencil className="h-4 w-4 mr-2" />
            <h2 className="text-xl font-semibold">Documents & SOPs</h2>
          </div>
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-3">
              <input
                type="text"
                placeholder="Search documents..."
                value={searchTerm}
                onChange={handleSearchChange}
                className="border rounded px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brass-500"
                maxWidth="150px"
              />
              <select
                value={filterType}
                onChange={handleFilterChange}
                className="border rounded px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brass-500 ml-2"
              >
                <option value="all">All Documents</option>
                <option value="sop">SOPs Only</option>
                <option value="template">Templates Only</option>
                <option value="report">Reports Only</option>
              </select>
            </div>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Create, manage, and deploy documents, SOPs, and agent templates
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {documents.map((doc) => (
          <div key={doc.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center mb-2">
                  <div className="w-8 h-8 bg-brass-500/10 rounded-full flex items-center justify-center">
                    <Pencil className="h-4 w-4 text-brass-500" />
                  </div>
                  <div className="ml-3">
                    <h3 className="font-semibold text-foreground truncate max-w-xs">
                      {doc.title}
                    </h3>
                    <p className="text-sm text-muted-foreground truncate">
                      {doc.description}
                    </p>
                    {doc.version && (
                      <p className="text-xs text-muted-foreground">
                        v{doc.version}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-end space-x-3">
                <div className="text-xs text-muted-foreground">
                  Type: {doc.type || 'N/A'}
                </div>
                {doc.status === 'active' && (
                  <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800">
                    Active
                  </span>
                )}
                {doc.status === 'draft' && (
                  <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800">
                    Draft
                  </span>
                )}
                {doc.status === 'archived' && (
                  <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700">
                    Archived
                  </span>
                )}
                <div className="mt-2 flex space-x-2">
                  <button
                    onClick={() => console.log('View document:', doc.id)}
                    className="px-3 py-1 text-xs bg-brass-500/10 hover:bg-brass-500/20 rounded"
                  >
                    View
                  </button>
                  <button
                    onClick={() => console.log('Use template:', doc.id)}
                    className="px-3 py-1 text-xs bg-brass-500/10 hover:bg-brass-500/20 rounded"
                  >
                    Use
                  </button>
                  <button
                    onClick={() => console.log('Delete document:', doc.id)}
                    className="px-3 py-1 text-xs text-destructive bg-transparent hover:bg-destructive/10 rounded"
                  >
                    Delete
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