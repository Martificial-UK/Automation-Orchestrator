
import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/Layout';
import { systemAPI, HealthStatus, leadsAPI, campaignsAPI, Lead, Campaign } from '@/services/api';

export const DashboardPage: React.FC = () => {
  const [metrics, setMetrics] = useState<HealthStatus | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      systemAPI.getDetailedHealth().then(res => setMetrics(res.data)),
      leadsAPI.getAll().then(res => setLeads(res.data)),
      campaignsAPI.getAll().then(res => setCampaigns(res.data)),
    ])
      .catch(() => setError('Failed to load dashboard data'))
      .finally(() => setLoading(false));
  }, []);

  // Calculate leads converted (status === 'converted')
  const leadsConverted = leads.filter(l => l.status === 'converted').length;
  // Calculate total sales (sum of all campaign metrics.converted)
  const totalSales = campaigns.reduce((sum, c) => sum + (c.metrics?.converted ?? 0), 0);
  // Simulate revenue (e.g., $100 per sale)
  const revenue = totalSales * 100;

  return (
    <DashboardLayout>
      <h1 className="text-2xl font-bold mb-4">Dashboard Overview</h1>
      {loading && <div>Loading dashboard...</div>}
      {error && <div className="text-red-500">{error}</div>}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded shadow p-6">
          <div className="text-gray-500">Leads Converted</div>
          <div className="text-xl font-bold">{leadsConverted}</div>
        </div>
        <div className="bg-white rounded shadow p-6">
          <div className="text-gray-500">Total Sales</div>
          <div className="text-xl font-bold">{totalSales}</div>
        </div>
        <div className="bg-white rounded shadow p-6">
          <div className="text-gray-500">Revenue</div>
          <div className="text-xl font-bold">${revenue.toLocaleString()}</div>
        </div>
        {metrics && (
          <div className="bg-white rounded shadow p-6">
            <div className="text-gray-500">System Status</div>
            <div className="text-xl font-bold">{metrics.status}</div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};


