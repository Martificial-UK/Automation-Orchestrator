# Workflow Builder Tutorial

A complete step-by-step guide to creating automation workflows using the visual Workflow Builder - no coding required!

---

## Table of Contents

1. [What is a Workflow?](#what-is-a-workflow)
2. [Accessing the Builder](#accessing-the-builder)
3. [Understanding Components](#understanding-components)
4. [Building Your First Workflow](#building-your-first-workflow)
5. [Common Workflow Templates](#common-workflow-templates)
6. [Advanced Techniques](#advanced-techniques)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## What is a Workflow?

A workflow automates a series of actions based on triggers and conditions. Think of it as a recipe:

**Example Workflow:**
```
TRIGGER: New lead added to system
  ↓
CONDITION: Lead's company size > 50 employees?
  ↓
ACTION: Send welcome email
  ↓
ACTION: Create task to follow up
  ↓
ACTION: Add "enterprise" tag
```

### Why Use Workflows?

✅ **Save Time**: Automate repetitive tasks (no manual work)
✅ **Consistency**: Same actions execute every time (no mistakes)
✅ **Scale**: Handle hundreds of leads automatically
✅ **Smart Automation**: Use conditions to vary actions based on data

---

## Accessing the Builder

### Step 1: Open Workflow Builder

1. Log into your dashboard at `http://localhost:8000`
2. Click **Builder** in the left sidebar
3. You'll see the Workflow Builder interface with:
   - Workflow name/description fields (top)
   - Step canvas (center) - where you design the workflow
   - Action buttons (Save, Publish)

### Step 2: Understand the Canvas

The canvas is your design area:
- **Blue boxes** = Triggers (what starts the workflow)
- **Green boxes** = Actions (what the workflow does)
- **Yellow boxes** = Conditions (if/then logic)
- **Connect them** = Create the workflow sequence

---

## Understanding Components

### 1. Triggers (What Starts a Workflow)

Triggers are events that launch your workflow:

#### Available Triggers:

| Trigger | Activated When |
|---------|---|
| **New Lead** | A new lead is added to system |
| **On Schedule** | Time-based (daily, weekly, monthly) |
| **Webhook** | External system sends data |
| **Campaign Sent** | Email/campaign completes |

**Example Implementations:**
- "On Schedule" → Run daily report every morning at 9am
- "New Lead" → Send welcome email when lead joins
- "Webhook" → Sync data from external CRM
- "Campaign Sent" → Archive completed campaign

---

### 2. Actions (What Happens in Workflow)

Actions are tasks your workflow performs:

#### Available Actions:

| Action | Does |
|--------|------|
| **Send Email** | Email lead/contact with predefined template |
| **Create Campaign** | Launch new marketing campaign automatically |
| **Add Tag** | Categorize lead (e.g., "nurture", "vip", "sales") |
| **HTTP Request** | Call external API or webhook |
| **Create Task** | Generate reminder/to-do for team |
| **Send Slack Message** | Notify team in Slack channel |

**Example Implementations:**
- Send Email → Welcome new prospects
- Create Campaign → Auto-launch nurture sequence
- Add Tag → Segment leads for targeting
- Create Task → Alert sales team of hot leads
- Send Slack → Notify when VIP lead joins

---

### 3. Conditions (Smart If/Then Logic)

Conditions make workflows intelligent - they execute different actions based on lead properties:

#### Available Conditions:

| Condition Type | Example |
|---|---|
| **Field Equals** | If Industry = "Technology" |
| **Field Contains** | If Email contains "@company.com" |
| **Date Passed** | If Last Contact > 30 days ago |

**Example Implementations:**
- If Industry = "Technology" → Add to tech_segment tag
- If Email contains "@gmail.com" → Different messaging
- If Date Passed = 14 days → Send re-engagement email

---

## Building Your First Workflow

### Project: Welcome Email for New Leads

Let's create a simple workflow that sends a welcome email to every new lead.

#### Step 1: Name Your Workflow

1. In the Workflow Builder form:
   - **Workflow Name**: `Welcome New Leads`
   - **Description**: `Send personalized welcome email to new leads`
2. These aren't required but help identify your workflow

#### Step 2: Add a Trigger

1. On the canvas, look for **Trigger buttons** or click "+ Add Trigger"
2. Select **New Lead** from the trigger list
3. A blue box appears on canvas labeled "New Lead"

#### Step 3: Add an Action

1. Click "+ Add Step" below the trigger
2. Select **Send Email** from Actions
3. A green box appears, connected to the trigger
4. Configure the action:
   - **Email Template**: Select "Welcome Email" or create custom
   - **Recipients**: "Lead Email" (auto-filled)
   - **Subject**: "Welcome to our service!"

#### Step 4: Save the Workflow

1. Click the **Save** button (bottom right)
2. Workflow saves to system
3. You'll see confirmation message

#### Step 5: Publish to Production

1. Click the **Publish** button
2. Workflow becomes active
3. Will execute on every future "New Lead" trigger

**Result**: Every time a new lead is added, they automatically receive a welcome email!

---

## Common Workflow Templates

The Workflow Builder includes pre-built templates to jump-start your workflows.

### Template 1: Welcome Email

**What it does**: Sends welcome email when new lead arrives

```
Trigger: New Lead
  ↓
Action: Send Email (Welcome template)
```

**Setup time**: < 1 minute
**Use case**: Immediate first contact with prospect

---

### Template 2: Daily Report

**What it does**: Sends daily summary email with metrics

```
Trigger: On Schedule (Daily at 9am)
  ↓
Action: Send Email (Daily Report template)
```

**Setup time**: < 2 minutes
**Use case**: Morning briefing for sales team

---

### Template 3: Auto-Tag Leads

**What it does**: Tags high-value leads automatically

```
Trigger: New Lead
  ↓
Condition: Company Size > 50 employees?
  ├─ YES → Action: Add Tag "enterprise"
  └─ NO → Action: Add Tag "small_business"
```

**Setup time**: 3-5 minutes
**Use case**: Segment leads for targeted campaigns

---

### Template 4: Auto-Campaign

**What it does**: Creates campaign when condition met

```
Trigger: On Schedule (Weekly)
  ↓
Action: Create Campaign (Scheduled Campaign template)
```

**Setup time**: 2-3 minutes
**Use case**: Regular automated campaigns

---

## Advanced Techniques

### Technique 1: Branching Logic with Conditions

Create workflows with different paths based on conditions:

```
Trigger: New Lead
  ↓
Condition: Lead Source = Direct?
  ├─ YES →  Action: Add Tag "direct_lead"
  │         Action: Send Email (Direct template)
  │
  └─ NO → Action: Add Tag "referred_lead"
          Action: Send Email (Referred template)
```

**Steps:**
1. Add trigger "New Lead"
2. Click "Add Condition"
3. Set "Lead Source = Direct"
4. Add actions to YES branch
5. Add actions to NO branch

---

### Technique 2: Multi-Step Workflows

Create complex sequences with multiple sequential actions:

```
Trigger: Campaign Sent
  ↓
Action 1: Add Tag "contacted"
  ↓
Action 2: Create Task "Follow up in 3 days"
  ↓
Action 3: Send Slack notification
  ↓
Action 4: Log event to database
```

**Steps:**
1. Add each action sequentially
2. Each step waits for previous to complete
3. If any step fails, workflow stops (shows in logs)
4. Monitor completion in Workflows list

---

### Technique 3: External Integrations

Use HTTP Request to connect external systems:

```
Trigger: New Lead
  ↓
Action: HTTP Request
  URL: https://api.example.com/webhooks/new-lead
  Method: POST
  Headers: Authorization: Bearer YOUR_TOKEN
  Body: { "email": "{lead_email}", "name": "{lead_name}" }
```

**Setup:**
1. Add "HTTP Request" action
2. Enter external API URL
3. Set authentication headers
4. Use {field_name} to include lead data
5. Test with sample data

---

## Best Practices

### 1. **Start Simple**

❌ DON'T: Create complex 10-step workflow immediately
✅ DO: Build simple 2-3 step workflows first, add complexity gradually

### 2. **Test Before Publishing**

- Use "Save" to test workflow logic
- Check workflow history for execution logs
- Verify actions execute correctly
- Only then click "Publish"

### 3. **Clear Naming**

❌ DON'T: Name workflows "Workflow1", "Auto2"
✅ DO: Name by purpose - "Welcome New Leads", "Daily Report"

### 4. **Monitor Execution**

- Visit **Workflows** page regularly
- Check success rates > 95%
- Review last run times
- Fix failures immediately

### 5. **Use Conditions Wisely**

❌ DON'T: Create too many branching paths (confusing)
✅ DO: Limit to 2-3 conditions per workflow (clear logic)

### 6. **Handle Errors**

- Plan for what happens if action fails
- Use conditions to prevent errors (verify data exists)
- Set up Slack notifications for failures
- Monitor queue depth for bottlenecks

### 7. **Document Your Workflows**

- Use descriptive names
- Add clear descriptions
- Note workflow purpose in team docs
- Share with team members

---

## Troubleshooting

### Problem: Workflow Not Executing

**Symptom**: Trigger condition met but workflow didn't run

**Solutions**:
1. Check workflow status = "Active" (not Paused)
2. Verify trigger matches your use case
3. Check system health dashboard (queue depth)
4. Review workflow execution logs

### Problem: Actions Executing in Wrong Order

**Symptom**: Tasks happening before previous task completes

**Solutions**:
1. Workflow steps execute sequentially - this might be working correctly
2. Check action configuration (verify it's set to wait)
3. Review action logs for timing
4. Contact support if behavior unexpected

### Problem: Condition Not Working

**Symptom**: All leads triggering regardless of condition

**Solutions**:
1. Verify condition is properly configured
2. Check field names match your data (case-sensitive)
3. Test with known data
4. Try simpler condition first

### Problem: Can't Connect to External API

**Symptom**: HTTP Request action shows errors

**Solutions**:
1. Verify URL is correct and accessible
2. Test URL in browser first
3. Check authentication credentials
4. Verify firewall allows outbound connections
5. Check API documentation for format requirements

---

## Example Workflows You Can Create

### Lead Nurture Sequence
```
Trigger: New Lead
  ↓
Condition: Industry = Required customer industry?
  ├─ YES → Send email 1 (Day 0)
  │      → Create task (Day 3 follow-up)
  │      → If no response after 7 days, send email 2
  └─ NO → Add tag "not_interested"
```

### Sales Alerts
```
Trigger: New Lead
  ↓
Condition: Deal size > $10,000?
  ├─ YES → Send Slack notification (sales channel)
  │      → Create task (urgent follow-up)
  │      → Add tag "high_value"
  └─ NO → Normal processing
```

### Compliance Workflow
```
Trigger: Campaign Sent
  ↓
Action: Create Task (Compliance check)
  ↓
Action: Log event to database
  ↓
Action: Send manager notification
```

---

## Tips & Tricks

**Keyboard Shortcuts**:
- `Ctrl+S`: Save workflow
- `Ctrl+Z`: Undo (if available)

**Quick Actions**:
- Click template to auto-populate common workflows
- Hover over steps to see configuration details
- Use search to find specific templates quickly

**Performance**:
- Keep workflows under 10 steps for speed
- Avoid excessive conditions (slows execution)
- Test complex workflows during off-hours
- Monitor execution times

---

## Support

- Check workflow status in **Workflows** page
- Review execution history for errors
- See [USER_GUIDE.md](USER_GUIDE.md) for dashboard help
- See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for technical details

---

## Next Steps

1. **Create your first workflow** using the templates
2. **Test thoroughly** before publishing
3. **Monitor execution** in the Workflows page
4. **Iterate and improve** based on results
5. **Share workflows** with your team

Happy automating!
