# User Guide: Automation Orchestrator Dashboard

Welcome to the Automation Orchestrator Dashboard! This comprehensive guide covers all features and how to use them effectively for your business automation needs.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Lead Management](#lead-management)
4. [Campaign Management](#campaign-management)
5. [Workflows & Automation](#workflows--automation)
6. [Analytics & Reporting](#analytics--reporting)
7. [Settings & Configuration](#settings--configuration)
8. [Best Practices](#best-practices)

---

## Getting Started

### Logging In

1. Navigate to your dashboard URL (e.g., `http://localhost:8000`)
2. Enter your credentials:
   - **Default Username**: `admin@example.com`
   - **Default Password**: `admin123`
3. Click **Login**
4. You'll be redirected to the main dashboard

**Security Tip**: Change your default password immediately in Settings after first login.

### Understanding the Interface

- **Sidebar Navigation** (left): Access all main features
- **Header** (top): Account info and quick actions
- **Main Content Area**: Feature-specific interface changes here
- **Responsive Design**: Works on desktop, tablet, and mobile

---

## Dashboard Overview

The **Dashboard** is your home page showing real-time system metrics and key performance indicators.

### Dashboard Metrics

#### 1. **Total Requests** Card
- Shows total API requests processed since system launch
- Indicates system usage and activity level
- Resets when server restarts

#### 2. **Success Rate** Card
- Percentage of successful workflow executions
- Target: >95% for production systems
- Green indicator = healthy (>90%)
- Red indicator = needs attention (<80%)

#### 3. **System Uptime** Card
- How long the system has been running without interruption
- Format: Days, Hours, Minutes, Seconds
- Critical metric for reliability assessment

#### 4. **Queue Depth** Card
- Number of tasks waiting to be processed
- Low numbers = responsive system
- High numbers = system is busy or backed up
- Investigate if consistently >100 tasks

### Real-Time Updates

The dashboard refreshes automatically every 30 seconds with the latest data. You can manually refresh by:
- Clicking the refresh icon (if present)
- Pressing F5 or Ctrl+R

---

## Lead Management

The **Leads** page is where you manage your customer/prospect database.

### Viewing Leads

1. Click **Leads** in the sidebar
2. See table of all leads with columns:
   - **Name**: Contact name
   - **Email**: Email address
   - **Status**: Current lead status (New, Contacted, Qualified, Converted)
   - **Created**: Date lead was added
   - **Actions**: Edit or delete buttons

### Creating a New Lead

1. Click the **+ New Lead** button (top right)
2. Fill in the form:
   - **Name** (required): Full name of the contact
   - **Email** (required): Valid email address
   - **Phone** (optional): Contact phone number
   - **Company** (optional): Company name
   - **Status** (optional): Select from dropdown (New, Contacted, Qualified, Converted)
   - **Notes** (optional): Any additional information
3. Click **Save**
4. New lead appears in the table

### Editing a Lead

1. Find the lead in the table
2. Click the **Edit** button (pencil icon)
3. Update any fields in the form
4. Click **Save Changes**
5. Changes apply immediately

### Deleting a Lead

1. Find the lead in the table
2. Click the **Delete** button (trash icon)
3. Confirm deletion in the popup
4. Lead is permanently removed

### Searching Leads

1. In the Leads page header, use the **Search** box
2. Type name, email, or any keyword
3. Results filter in real-time
4. Clear search by deleting text or clicking X

### Lead Status Management

Update a lead's status as they progress through your sales pipeline:
- **New**: Just added to system
- **Contacted**: Initial contact made
- **Qualified**: Meets criteria for your product/service
- **Converted**: Became a customer

---

## Campaign Management

The **Campaigns** page lets you manage and monitor your marketing and automation campaigns.

### Viewing Campaigns

1. Click **Campaigns** in the sidebar
2. See campaign cards in a grid layout showing:
   - **Campaign Name**: Title of the campaign
   - **Type**: Email, SMS, Workflow, etc.
   - **Status**: Active, Paused, Completed, Draft
   - **Performance Metrics**: 
     - Sent count
     - Open rate
     - Click rate
     - Conversion rate

### Creating a Campaign

1. Click **+ New Campaign** button
2. Fill the campaign details form:
   - **Name** (required): Descriptive campaign name
   - **Type** (required): Select campaign type from dropdown
   - **Description**: Purpose and goals of campaign
   - **Start Date**: When campaign begins
   - **End Date**: When campaign ends
   - **Target Audience**: Filters for lead selection
3. Click **Create Campaign**
4. New campaign appears in the grid

### Campaign Status Indicators

- **Green** = Active/Running well
- **Yellow** = Paused/Needs attention
- **Gray** = Completed
- **Blue** = Draft (not yet launched)

### Monitoring Campaign Performance

For each campaign card:
- **Sent**: Total messages/emails sent
- **Open Rate**: % of recipients who opened (email campaigns)
- **Click Rate**: % who clicked links
- **Conversion Rate**: % who completed desired action

### Pausing a Campaign

1. Find the campaign card
2. Click the **Pause** button
3. Campaign stops immediately (tasks in queue still process)
4. Resume clicking the **Resume** button

### Deleting a Campaign

1. Find the campaign card
2. Click **Delete**
3. Confirm in popup
4. Campaign and all associated data removed

---

## Workflows & Automation

The **Workflows** page shows all your automation workflows and their execution status.

### Understanding Workflows

A workflow is an automated sequence of actions triggered by events. Example:
- **Trigger**: New lead added to system
- **Actions**: Send welcome email → Add tag "nurture" → Create calendar reminder
- **Result**: All actions execute automatically when trigger occurs

### Viewing Active Workflows

1. Click **Workflows** in the sidebar
2. See list of workflow configurations:
   - **Name**: Workflow identifier
   - **Trigger**: What starts this workflow
   - **Status**: Active or Inactive
   - **Last Run**: When workflow last executed
   - **Success Rate**: % of successful executions

### Monitoring Workflows

For each workflow:
- Click **View Details** to see execution history
- Check **Last Run** time to confirm workflow is working
- Monitor **Success Rate** - target >95%
- Click **Run Now** to manually trigger workflow

### Pausing a Workflow

1. Find the workflow in the list
2. Click **Pause** button
3. Workflow stops executing
4. Resume anytime with **Resume** button

---

## Using the Workflow Builder

The **Workflow Builder** (accessed via sidebar) is a visual, no-code interface for creating automation workflows without programming knowledge.

**→ See [WORKFLOW_BUILDER_TUTORIAL.md](WORKFLOW_BUILDER_TUTORIAL.md) for detailed workflow creation guide**

---

## Analytics & Reporting

The **Analytics** page provides charts and insights into your system performance.

### Available Charts

#### 1. **Lead Status Distribution** (Pie Chart)
Shows breakdown of leads by status:
- New: Unqualified new leads
- Contacted: Initial outreach completed
- Qualified: Meet your criteria
- Converted: Became customers
- Use to identify bottlenecks in your sales process

#### 2. **Campaign Performance** (Bar Chart)
Compares open rates across all campaigns:
- X-axis: Campaign names
- Y-axis: Percentage (0-100%)
- Taller bars = better engagement
- Identify your highest-performing campaigns

#### 3. **Request Trends** (Line Chart)
Shows API request volume over time:
- Helps identify peak usage periods
- Useful for capacity planning
- Sudden spikes indicate increased activity

#### 4. **Workflow Execution Results** (Pie Chart)
Breakdown of workflow runs:
- Success: Completed without errors
- Failed: Encountered errors
- Retry: Currently being retried
- Monitor for high failure rates

### Using Analytics

- **Hover over data**: See exact values
- **Legend toggle**: Click legend items to show/hide data series
- **Export ideas**: Screenshot or export for presentations
- **Date ranges**: Check monthly/weekly performance trends

---

## Settings & Configuration

The **Settings** page manages your account and system configuration.

### Account Settings

#### Profile Section
- **Full Name**: Your display name
- **Email**: Account email address
- **Timezone**: Set for date/time references
- Update and click **Save Profile**

### API Keys

API keys allow external systems to interact with your automation system.

#### Creating an API Key
1. Click **Generate New API Key** button
2. Give the key a descriptive name
3. Click **Generate**
4. **Copy immediately** (won't be shown again)
5. Store securely in password manager

#### Using API Keys
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/leads
```

#### Revoking an API Key
1. Find the key in the list
2. Click **Revoke**
3. Confirm
4. Key immediately stops working

### Trial Information

View your trial status:
- **Days Remaining**: How long trial is active
- **Workflows Remaining**: Usage limit
- **Request Limit**: API calls allowed per day
- **Upgrade Button**: To convert to paid plan

###System Health

Real-time system status:
- **Status**: Up/Down indicator
- **Response Time**: Average API response (ms)
- **Error Rate**: % of failed requests (target <5%)
- **Database Status**: Connected/Disconnected
- **Queue Service**: Redis status / Fallback mode

### User Management

- **Change Password**: Set new account password
- **Two-Factor Auth**: Enable for security (future feature)
- **Session Manager**: View active sessions and sign out remotely

---

## Best Practices

### 1. **Lead Organization**

- Create descriptive lead names (full names)
- Maintain consistent email format
- Use status field to track pipeline progress
- Add notes for follow-up context
- Regular lead cleanup (remove duplicates)

### 2. **Campaign Strategy**

- Use meaningful campaign names
- Set realistic date ranges
- Monitor performance metrics weekly
- Pause underperforming campaigns
- Test with small audience first

### 3. **Workflow Design**

- Start with simple workflows (1-2 actions)
- Use clear trigger events
- Include error handling/retry logic
- Monitor execution rates
- Document workflow purpose in description

### 4. **System Maintenance**

- Check dashboard health metrics daily
- Review analytics weekly
- Clean up old/completed campaigns
- Archive inactive workflows
- Backup important lead data regularly

### 5. **Security**

- Change default password immediately
- Rotate API keys quarterly
- Use strong, unique passwords
- Don't share API keys
- Review settings periodically

### 6. **Performance Optimization**

- Keep workflows under 10 steps for speed
- Batch similar leads for campaigns
- Monitor queue depth - process large batches in steps
- Avoid excessive scheduled triggers (max 1 per minute)
- Archive old data to keep system responsive

---

## Troubleshooting

### Dashboard Not Loading
1. Clear browser cache (Ctrl+Shift+Delete)
2. Check internet connection
3. Verify server is running (`http://localhost:8000/health`)
4. Try incognito/private window

### Can't Login
1. Verify username/password correct
2. Try default credentials: `admin@example.com` / `admin123`
3. Check browser console for errors (F12)
4. Clear stored tokens: Settings → Logout everywhere

### Workflow Not Executing
1. Check workflow status = Active (not Paused)
2. Verify trigger conditions match real events
3. Check system health metrics (queue depth)
4. Review workflow execution history
5. Check API keys if using external triggers

### Slow Performance
1. Check system uptime (may need restart)
2. Monitor queue depth (high = backlog)
3. Clear old campaigns/workflows
4. Check browser: disable extensions, clear cache
5. Check internet connection speed

---

## Support & Resources

- **API Documentation**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Workflow Builder Guide**: [WORKFLOW_BUILDER_TUTORIAL.md](WORKFLOW_BUILDER_TUTORIAL.md)
- **Production Deployment**: [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md)
- **Monitoring Setup**: [PRODUCTION_MONITORING_SETUP.md](PRODUCTION_MONITORING_SETUP.md)

---

## Version Information

- **Dashboard Version**: 1.0.0
- **Last Updated**: February 2026
- **Supported Browsers**: Chrome, Firefox, Safari, Edge (latest versions)

---

For additional help or feature requests, contact support or check the [README.md](README.md).
