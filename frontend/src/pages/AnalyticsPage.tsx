import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/Layout';
import { systemAPI, leadsAPI, campaignsAPI, Metrics, Lead, Campaign } from '@/services/api';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, Users, Megaphone, Activity } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  type AnalyticsMetrics = {
    system: Metrics;
    leads: Lead[];
    campaigns: Campaign[];
  };

  type LeadStatusMap = Record<string, number>;

  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [metricsRes, leadsRes, campaignsRes] = await Promise.all([
          systemAPI.getMetrics(),
          leadsAPI.getAll(),
          campaignsAPI.getAll(),
        ]);
        
        setMetrics({
          system: metricsRes.data,
          leads: leadsRes.data,
          campaigns: campaignsRes.data,
        });
      } catch (error) {
        console.error('Error fetching analytics:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </DashboardLayout>
    );
  }

  const systemMetrics = metrics?.system;
  const successRate = systemMetrics && systemMetrics.requests_total > 0
    ? ((1 - systemMetrics.requests_failed / systemMetrics.requests_total) * 100)
    : 0;

  // Prepare chart data
  const leadStatusData = metrics?.leads?.reduce<LeadStatusMap>((acc, lead) => {
    const status = lead.status || 'new';
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(leadStatusData || {}).map(([name, value]) => ({
    name,
    value,
  }));

  const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444'];

  const campaignPerformanceData = metrics?.campaigns?.map((campaign) => ({
    name: campaign.name.substring(0, 15),
    sent: campaign.metrics?.sent || 0,
    opened: campaign.metrics?.opened || 0,
    clicked: campaign.metrics?.clicked || 0,
  })) || [];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
          <p className="mt-1 text-sm text-gray-500">Performance insights and metrics</p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-blue-100 rounded-md p-3">
                  <Users className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Total Leads</dt>
                    <dd className="text-2xl font-semibold text-gray-900">
                      {metrics?.leads?.length || 0}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-green-100 rounded-md p-3">
                  <Megaphone className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Active Campaigns</dt>
                    <dd className="text-2xl font-semibold text-gray-900">
                      {metrics?.campaigns?.filter((campaign) => campaign.status === 'active').length || 0}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-purple-100 rounded-md p-3">
                  <Activity className="h-6 w-6 text-purple-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">API Requests</dt>
                    <dd className="text-2xl font-semibold text-gray-900">
                      {metrics?.system?.requests_total?.toLocaleString() || 0}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-orange-100 rounded-md p-3">
                  <TrendingUp className="h-6 w-6 text-orange-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Success Rate</dt>
                    <dd className="text-2xl font-semibold text-gray-900">
                      {successRate.toFixed(1)}%
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Lead Status Distribution */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Lead Status Distribution</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Campaign Performance */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Campaign Performance</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={campaignPerformanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="sent" fill="#0ea5e9" />
                <Bar dataKey="opened" fill="#10b981" />
                <Bar dataKey="clicked" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* System Performance */}
        {metrics?.system && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">System Performance</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-sm text-gray-500">Avg Response Time</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {(metrics.system.avg_latency_ms / 1000).toFixed(2)}s
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Max Latency</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {(metrics.system.max_latency_ms / 1000).toFixed(2)}s
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Uptime</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {Math.floor(metrics.system.uptime_seconds / 3600)}h {Math.floor((metrics.system.uptime_seconds % 3600) / 60)}m
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Queue Depth</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {metrics.system.queue_depth || 0}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};
