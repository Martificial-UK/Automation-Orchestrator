

import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/Layout';
import { systemAPI, HealthStatus } from '@/services/api';

export const AnalyticsPage: React.FC = () => {
  const [metrics, setMetrics] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    systemAPI.getDetailedHealth()
      .then(res => setMetrics(res.data))
      .catch(() => setError('Failed to load analytics'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout>
      <h1 className="text-2xl font-bold mb-4">Analytics</h1>
      {loading && <div>Loading analytics...</div>}
      {error && <div className="text-red-500">{error}</div>}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded shadow p-6">
            <div className="text-gray-500">Database Status</div>
            <div className="text-xl font-bold">{metrics.database?.status ?? 'N/A'}</div>
          </div>
          <div className="bg-white rounded shadow p-6">
            <div className="text-gray-500">Queue Status</div>
            <div className="text-xl font-bold">{metrics.queue?.status ?? 'N/A'}</div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};


