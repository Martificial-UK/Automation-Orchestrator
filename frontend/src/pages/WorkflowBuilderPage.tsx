import React, { useState } from 'react';
import { DashboardLayout } from '@/components/Layout';
import { workflowsAPI } from '@/services/api';
import { Plus, ArrowRight, Trash2, Save } from 'lucide-react';

interface WorkflowStep {
  id: string;
  type: 'trigger' | 'action' | 'condition';
  label: string;
  config: Record<string, unknown>;
}

interface WorkflowPayload {
  name: string;
  description: string;
  steps: WorkflowStep[];
  enabled: boolean;
}

const TRIGGERS = [
  { value: 'new_lead', label: 'New Lead Created' },
  { value: 'on_schedule', label: 'On Schedule (Daily/Weekly)' },
  { value: 'webhook', label: 'Webhook Received' },
  { value: 'campaign_sent', label: 'Campaign Sent' },
];

const ACTIONS = [
  { value: 'send_email', label: 'Send Email' },
  { value: 'create_campaign', label: 'Create Campaign' },
  { value: 'add_tag', label: 'Add Tag to Lead' },
  { value: 'http_request', label: 'Make HTTP Request' },
  { value: 'create_task', label: 'Create Task' },
  { value: 'send_slack', label: 'Send Slack Message' },
];

export const WorkflowBuilderPage: React.FC = () => {
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [saving, setSaving] = useState(false);
  const [showTriggerMenu, setShowTriggerMenu] = useState(false);
  const [showActionMenu, setShowActionMenu] = useState(false);

  const addTrigger = (triggerType: string) => {
    const trigger = TRIGGERS.find(t => t.value === triggerType);
    if (trigger) {
      setSteps([{
        id: `trigger-${Date.now()}`,
        type: 'trigger',
        label: trigger.label,
        config: { type: triggerType },
      }]);
      setShowTriggerMenu(false);
    }
  };

  const addAction = (actionType: string) => {
    const action = ACTIONS.find(a => a.value === actionType);
    if (action) {
      setSteps([...steps, {
        id: `action-${Date.now()}`,
        type: 'action',
        label: action.label,
        config: { type: actionType },
      }]);
      setShowActionMenu(false);
    }
  };

  const removeStep = (id: string) => {
    setSteps(steps.filter(s => s.id !== id));
  };

  const saveWorkflow = async () => {
    if (!workflowName || steps.length === 0) {
      alert('Please enter a workflow name and add at least one step');
      return;
    }

    setSaving(true);
    try {
      const payload: WorkflowPayload = {
        name: workflowName,
        description: workflowDescription,
        steps: steps,
        enabled: true,
      };
      await workflowsAPI.trigger(payload);
      alert('Workflow saved successfully!');
      setWorkflowName('');
      setWorkflowDescription('');
      setSteps([]);
    } catch (error) {
      console.error('Error saving workflow:', error);
      alert('Failed to save workflow');
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Workflow Builder</h1>
          <p className="mt-1 text-sm text-gray-500">Create automated workflows without coding</p>
        </div>

        {/* Workflow Details */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Workflow Details</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Workflow Name</label>
              <input
                type="text"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                placeholder="e.g., Welcome New Leads"
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Description (Optional)</label>
              <textarea
                value={workflowDescription}
                onChange={(e) => setWorkflowDescription(e.target.value)}
                placeholder="Describe what this workflow does..."
                rows={3}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>
          </div>
        </div>

        {/* Workflow Builder */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Build Your Workflow</h2>
          
          {/* Steps Visualization */}
          <div className="space-y-3 mb-6">
            {steps.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>Start by adding a trigger</p>
              </div>
            ) : (
              <>
                {steps.map((step, index) => (
                  <div key={step.id}>
                    <div className={`flex items-center justify-between p-4 border-2 rounded-lg ${
                      step.type === 'trigger' ? 'border-blue-200 bg-blue-50' :
                      step.type === 'action' ? 'border-green-200 bg-green-50' :
                      'border-yellow-200 bg-yellow-50'
                    }`}>
                      <div>
                        <p className="font-semibold text-gray-900">{step.label}</p>
                        <p className="text-xs text-gray-500 capitalize">{step.type}</p>
                      </div>
                      <button
                        onClick={() => removeStep(step.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                    {index < steps.length - 1 && (
                      <div className="flex justify-center py-2">
                        <ArrowRight className="h-5 w-5 text-gray-400 transform rotate-90" />
                      </div>
                    )}
                  </div>
                ))}
              </>
            )}
          </div>

          {/* Add Steps Buttons */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {/* Add Trigger */}
            {steps.length === 0 && (
              <div className="relative">
                <button
                  onClick={() => setShowTriggerMenu(!showTriggerMenu)}
                  className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Trigger
                </button>
                {showTriggerMenu && (
                  <div className="absolute top-full right-0 mt-2 w-56 bg-white border border-gray-300 rounded-lg shadow-lg z-10">
                    {TRIGGERS.map((trigger) => (
                      <button
                        key={trigger.value}
                        onClick={() => addTrigger(trigger.value)}
                        className="w-full text-left px-4 py-2 hover:bg-gray-100 first:rounded-t-lg last:rounded-b-lg"
                      >
                        {trigger.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Add Action */}
            {steps.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setShowActionMenu(!showActionMenu)}
                  className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Action
                </button>
                {showActionMenu && (
                  <div className="absolute top-full left-0 mt-2 w-56 bg-white border border-gray-300 rounded-lg shadow-lg z-10">
                    {ACTIONS.map((action) => (
                      <button
                        key={action.value}
                        onClick={() => addAction(action.value)}
                        className="w-full text-left px-4 py-2 hover:bg-gray-100 first:rounded-t-lg last:rounded-b-lg"
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Save Button */}
            <button
              onClick={saveWorkflow}
              disabled={saving || steps.length === 0}
              className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4 mr-2" />
              {saving ? 'Saving...' : 'Save Workflow'}
            </button>
          </div>
        </div>

        {/* Template Workflows */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Templates</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <button
              onClick={() => {
                setWorkflowName('Welcome New Leads');
                setSteps([
                  { id: '1', type: 'trigger', label: 'New Lead Created', config: { type: 'new_lead' } },
                  { id: '2', type: 'action', label: 'Send Email', config: { type: 'send_email' } },
                ]);
              }}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition"
            >
              <p className="font-semibold text-gray-900">Welcome Email</p>
              <p className="text-sm text-gray-500">Send welcome email to new leads</p>
            </button>

            <button
              onClick={() => {
                setWorkflowName('Daily Campaign Report');
                setSteps([
                  { id: '1', type: 'trigger', label: 'On Schedule (Daily/Weekly)', config: { type: 'on_schedule' } },
                  { id: '2', type: 'action', label: 'Make HTTP Request', config: { type: 'http_request' } },
                ]);
              }}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition"
            >
              <p className="font-semibold text-gray-900">Daily Report</p>
              <p className="text-sm text-gray-500">Send daily campaign performance report</p>
            </button>

            <button
              onClick={() => {
                setWorkflowName('Tag High-Value Leads');
                setSteps([
                  { id: '1', type: 'trigger', label: 'New Lead Created', config: { type: 'new_lead' } },
                  { id: '2', type: 'condition', label: 'If Field Equals', config: { type: 'if_field_equals' } },
                  { id: '3', type: 'action', label: 'Add Tag to Lead', config: { type: 'add_tag' } },
                ]);
              }}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition"
            >
              <p className="font-semibold text-gray-900">Tag Leads</p>
              <p className="text-sm text-gray-500">Automatically tag leads based on attributes</p>
            </button>

            <button
              onClick={() => {
                setWorkflowName('Campaign Workflow');
                setSteps([
                  { id: '1', type: 'trigger', label: 'On Schedule (Daily/Weekly)', config: { type: 'on_schedule' } },
                  { id: '2', type: 'action', label: 'Create Campaign', config: { type: 'create_campaign' } },
                ]);
              }}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition"
            >
              <p className="font-semibold text-gray-900">Auto Campaign</p>
              <p className="text-sm text-gray-500">Automatically create and send campaigns</p>
            </button>
          </div>
        </div>

        {/* Help Section */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-blue-900 mb-2">💡 How it works:</h3>
          <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
            <li>Choose a <strong>Trigger</strong> (what starts the workflow)</li>
            <li>Add <strong>Actions</strong> (what happens as a result)</li>
            <li>Optionally add <strong>Conditions</strong> (if/then logic)</li>
            <li>Save your workflow and it runs automatically</li>
          </ol>
        </div>
      </div>
    </DashboardLayout>
  );
};
