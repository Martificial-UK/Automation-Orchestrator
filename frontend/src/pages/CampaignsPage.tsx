import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/Layout';
import { campaignsAPI, Campaign } from '@/services/api';
import { Plus, TrendingUp } from 'lucide-react';

export const CampaignsPage: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCampaigns = async () => {
      try {
        const response = await campaignsAPI.getAll();
        setCampaigns(response.data);
      } catch (error) {
        console.error('Error fetching campaigns:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchCampaigns();
  }, []);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Campaigns</h1>
            <p className="mt-1 text-sm text-gray-500">Manage your marketing campaigns</p>
          </div>
          <button className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700">
            <Plus className="h-5 w-5 mr-2" />
            Create Campaign
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : campaigns.length > 0 ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {campaigns.map((campaign) => (
              <div key={campaign.id} className="bg-white overflow-hidden shadow rounded-lg hover:shadow-lg transition-shadow">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-medium text-gray-900 truncate">{campaign.name}</h3>
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      campaign.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : campaign.status === 'paused'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {campaign.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mb-4">{campaign.type || 'Email Campaign'}</p>
                  
                  {campaign.metrics && (
                    <div className="grid grid-cols-2 gap-4 border-t pt-4">
                      <div>
                        <p className="text-xs text-gray-500">Sent</p>
                        <p className="text-lg font-semibold text-gray-900">{campaign.metrics.sent || 0}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Opened</p>
                        <p className="text-lg font-semibold text-gray-900">{campaign.metrics.opened || 0}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Clicked</p>
                        <p className="text-lg font-semibold text-gray-900">{campaign.metrics.clicked || 0}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Converted</p>
                        <p className="text-lg font-semibold text-gray-900">{campaign.metrics.converted || 0}</p>
                      </div>
                    </div>
                  )}
                </div>
                <div className="bg-gray-50 px-6 py-3">
                  <button className="text-sm text-primary-600 hover:text-primary-900 font-medium">
                    View Details →
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white shadow sm:rounded-lg">
            <div className="px-4 py-12 text-center">
              <TrendingUp className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No campaigns</h3>
              <p className="mt-1 text-sm text-gray-500">Get started by creating a new campaign.</p>
              <div className="mt-6">
                <button className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700">
                  <Plus className="h-5 w-5 mr-2" />
                  New Campaign
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};
