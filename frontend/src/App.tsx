<<<<<<< HEAD
// import React from 'react';
=======
>>>>>>> b827fdb4458c7573c3e10cfdd001559a627ed4e1
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { ProtectedRoute } from '@/components/ProtectedRoute';
// import React from 'react';
import { DashboardPage } from '@/pages/DashboardPage';
import { LeadsPage } from '@/pages/LeadsPage';
import { CampaignsPage } from '@/pages/CampaignsPage';
import { WorkflowsPage } from '@/pages/WorkflowsPage';
<<<<<<< HEAD
=======
import { WorkflowBuilderPage } from '@/pages/WorkflowBuilderPage';
>>>>>>> b827fdb4458c7573c3e10cfdd001559a627ed4e1
import { WorkflowBuilderPage } from '@/pages/WorkflowBuilderPage';
import { AnalyticsPage } from '@/pages/AnalyticsPage';
import { SettingsPage } from '@/pages/SettingsPage';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/leads"
            element={
              <ProtectedRoute>
                <LeadsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns"
            element={
              <ProtectedRoute>
                <CampaignsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workflows"
            element={
              <ProtectedRoute>
                <WorkflowsPage />
              </ProtectedRoute>
            }
          />
          <Route
<<<<<<< HEAD
=======
            path="/builder"
            element={
              <ProtectedRoute>
                <WorkflowBuilderPage />
              </ProtectedRoute>
            }
          />
          <Route
>>>>>>> b827fdb4458c7573c3e10cfdd001559a627ed4e1
            path="/analytics"
            element={
              <ProtectedRoute>
                <AnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
