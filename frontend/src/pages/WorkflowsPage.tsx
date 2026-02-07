import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/Layout';
import { workflowsAPI, Workflow } from '@/services/api';
import { Play, Plus, Workflow as WorkflowIcon } from 'lucide-react';

export const WorkflowsPage: React.FC = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        const response = await workflowsAPI.getAll();
        setWorkflows(response.data);
      } catch (error) {
        console.error('Error fetching workflows:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchWorkflows();
  }, []);

  const handleTrigger = async (workflowId: string) => {
    try {
      await workflowsAPI.trigger({ workflow_id: workflowId, data: {} });
      alert('Workflow triggered successfully!');
    } catch (error) {
      console.error('Error triggering workflow:', error);
      alert('Failed to trigger workflow');
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Workflows</h1>
            <p className="mt-1 text-sm text-gray-500">Automate your business processes</p>
          </div>
          <button className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700">
            <Plus className="h-5 w-5 mr-2" />
            Create Workflow
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : workflows.length > 0 ? (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {workflows.map((workflow) => (
                <li key={workflow.id}>
                  <div className="px-6 py-5 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-medium text-gray-900">{workflow.name}</h3>
                        <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                            workflow.status === 'active' 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {workflow.status}
                          </span>
                          {workflow.trigger_type && (
                            <span>Trigger: {workflow.trigger_type}</span>
                          )}
                          {workflow.last_run && (
                            <span>Last run: {new Date(workflow.last_run).toLocaleString()}</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleTrigger(workflow.id)}
                        className="ml-4 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                      >
                        <Play className="h-4 w-4 mr-1" />
                        Run
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="bg-white shadow sm:rounded-lg">
            <div className="px-4 py-12 text-center">
              <WorkflowIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No workflows</h3>
              <p className="mt-1 text-sm text-gray-500">Get started by creating your first automation workflow.</p>
              <div className="mt-6">
                <button className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700">
                  <Plus className="h-5 w-5 mr-2" />
                  New Workflow
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};
