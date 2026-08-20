import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LandingPage } from '../pages/LandingPage';
import { LoginPage } from '../pages/auth/LoginPage';
import { RegisterPage } from '../pages/auth/RegisterPage';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';

import { ReportIssuePage } from '../pages/citizen/ReportIssuePage';
import { CitizenIssuesPage } from '../pages/citizen/CitizenIssuesPage';
import { CitizenIssueDetailPage } from '../pages/citizen/CitizenIssueDetailPage';
import { CitizenProposalsPage } from '../pages/citizen/CitizenProposalsPage';
import { CitizenProposalDetailPage } from '../pages/citizen/CitizenProposalDetailPage';
import { CitizenVotingPage } from '../pages/citizen/CitizenVotingPage';

import { OperatorDashboardPage } from '../pages/operator/OperatorDashboardPage';
import { OperatorMapPage } from '../pages/operator/OperatorMapPage';

import { VerificationQueuePage } from '../pages/supervisor/VerificationQueuePage';
import { SupervisorDashboardPage } from '../pages/supervisor/SupervisorDashboardPage';

import { PublicDashboardPage } from '../pages/public/PublicDashboardPage';
import { PublicOverviewPage } from '../pages/public/PublicOverviewPage';
import { PublicHotspotsPage } from '../pages/public/PublicHotspotsPage';

import { AdminDashboardPage } from '../pages/admin/AdminDashboardPage';
import { AdminRagPage } from '../pages/admin/AdminRagPage';

export const AppRouter: React.FC = () => {
  return (
    <Routes>
      {/* Public Landing & Authentication Pages */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Public Transparency Pages (Unauthenticated) */}
      <Route path="/public" element={<PublicOverviewPage />} />
      <Route path="/public/transparency" element={<PublicDashboardPage />} />
      <Route path="/public/hotspots" element={<PublicHotspotsPage />} />
      <Route path="/public/budget" element={<CitizenProposalsPage />} />
      <Route path="/public/issues/:id" element={<CitizenIssueDetailPage />} />

      {/* Citizen Portal Protected Routes */}
      <Route path="/citizen" element={<Navigate to="/citizen/issues" replace />} />
      <Route
        path="/citizen/report"
        element={
          <ProtectedRoute allowedRoles={['citizen', 'admin']}>
            <ReportIssuePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/citizen/issues"
        element={
          <ProtectedRoute allowedRoles={['citizen', 'admin']}>
            <CitizenIssuesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/citizen/issues/:id"
        element={
          <ProtectedRoute allowedRoles={['citizen', 'admin']}>
            <CitizenIssueDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/citizen/proposals"
        element={
          <ProtectedRoute allowedRoles={['citizen', 'admin']}>
            <CitizenProposalsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/citizen/proposals/:id"
        element={
          <ProtectedRoute allowedRoles={['citizen', 'admin']}>
            <CitizenProposalDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/citizen/budget"
        element={
          <ProtectedRoute allowedRoles={['citizen', 'admin']}>
            <CitizenProposalsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/citizen/voting"
        element={
          <ProtectedRoute allowedRoles={['citizen', 'admin']}>
            <CitizenVotingPage />
          </ProtectedRoute>
        }
      />

      {/* Operator Dashboard Protected Routes */}
      <Route
        path="/operator"
        element={
          <ProtectedRoute allowedRoles={['operator', 'admin']}>
            <OperatorDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/operator/issues/:id"
        element={
          <ProtectedRoute allowedRoles={['operator', 'admin']}>
            <OperatorDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/operator/map"
        element={
          <ProtectedRoute allowedRoles={['operator', 'admin']}>
            <OperatorMapPage />
          </ProtectedRoute>
        }
      />

      {/* Supervisor Protected Routes */}
      <Route
        path="/supervisor"
        element={
          <ProtectedRoute allowedRoles={['supervisor', 'admin']}>
            <SupervisorDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/supervisor/evidence"
        element={
          <ProtectedRoute allowedRoles={['supervisor', 'admin']}>
            <VerificationQueuePage />
          </ProtectedRoute>
        }
      />

      {/* Admin Protected Routes */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/rag"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminRagPage />
          </ProtectedRoute>
        }
      />

      {/* Catch-all redirect to Landing */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
