# ERP Reconciliation System - Features Documentation

## Overview
This ERP reconciliation system provides automated matching between bank transactions and invoices, with advanced notification and reporting capabilities.

## ✅ Core Features

### 1. Automatic Matching Logic
- **Reference Number Matching**: Exact match between transaction reference and invoice reference
- **Customer Name + Amount Matching**: Matches customer names found in transaction descriptions with exact amount
- **Partial Name Matching**: Handles partial customer name matches with confidence scoring
- **Amount-Only Matching**: Low confidence matching based on amount alone

### 2. Reconciliation Process
- Automatic status updates for matched transactions and paid invoices
- Comprehensive reconciliation logging with confidence scoring
- Manual matching capabilities for complex cases
- Bulk reconciliation processing

## 🆕 New Features

### 3. Notification System for Unmatched Transactions
**Automatically alerts finance teams when unmatched transactions exceed threshold**

#### Features:
- **Smart Threshold Detection**: Configurable threshold for triggering notifications
- **Email Alerts**: Detailed email notifications with transaction summaries
- **Rate Limiting**: Prevents spam by limiting notifications to once per hour
- **Comprehensive Logging**: Tracks all notification attempts and results

#### Configuration:
```python
# In settings.py
NOTIFICATION_SETTINGS = {
    'UNMATCHED_THRESHOLD': 5,  # Send notification when >= 5 unmatched transactions
    'NOTIFY_EMAILS': ['admin@example.com', 'finance@example.com'],
    'ENABLE_NOTIFICATIONS': True,
}

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

#### API Endpoints:
- `GET /api/notifications/` - View notification history
- `POST /api/notifications/` - Manually trigger notification
- `GET /api/notifications/settings/` - View current settings
- `POST /api/notifications/settings/` - Test notification system

### 4. PDF Export of Reconciliation Summary
**Generate comprehensive PDF reports of reconciliation activities**

#### Features:
- **Professional PDF Reports**: Clean, formatted reconciliation summaries
- **Date Range Filtering**: Generate reports for specific time periods
- **Comprehensive Statistics**: Transaction counts, match rates, payment rates
- **Unmatched Transaction Details**: Detailed listing of problematic transactions
- **Auto-generated Filenames**: Timestamped files for easy organization

#### API Endpoint:
- `GET /api/export/pdf/` - Generate PDF report
  - Optional parameters: `start_date` and `end_date` (format: YYYY-MM-DD)
  - Example: `/api/export/pdf/?start_date=2024-01-01&end_date=2024-01-31`

#### Report Contents:
1. **Summary Statistics Table**
   - Total transactions vs matched/unmatched counts
   - Invoice payment statistics
   - Auto vs manual match breakdown

2. **Unmatched Transactions Detail Table**
   - Transaction ID, date, amount
   - Description and reference number
   - Limited to first 20 transactions with count indicator

## 📊 API Endpoints Summary

### Enhanced Existing Endpoints
- `POST /api/bank/upload/` - Upload CSV with automatic reconciliation + notifications
- `GET /api/bank/unmatched/` - Get unmatched transactions
- `POST /api/bank/match/` - Manual transaction matching
- `GET /api/reconciliation/logs/` - Enhanced logs with detailed information
- `POST /api/reconciliation/bulk/` - Bulk reconciliation + notifications
- `POST /api/reconciliation/reprocess/` - Reprocess specific transaction

### New Notification Endpoints
- `GET /api/notifications/` - View notification history (last 20)
- `POST /api/notifications/` - Manually send unmatched transaction notification
- `GET /api/notifications/settings/` - View notification settings and current unmatched count
- `POST /api/notifications/settings/` - Test notification system

### New Export Endpoints
- `GET /api/export/pdf/` - Generate reconciliation summary PDF
  - Optional: `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

## 🔧 Setup Instructions

### 1. Install Dependencies
```bash
pip install reportlab pillow
```

### 2. Configure Email Settings
Update `settings.py` with your SMTP configuration:
```python
EMAIL_HOST = 'your-smtp-server.com'
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
NOTIFICATION_SETTINGS = {
    'NOTIFY_EMAILS': ['finance@yourcompany.com'],
    'UNMATCHED_THRESHOLD': 5,
    'ENABLE_NOTIFICATIONS': True,
}
```

### 3. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## 📈 Usage Examples

### Automatic Notifications
Notifications are triggered automatically when:
1. Bulk reconciliation finds unmatched transactions above threshold
2. CSV upload results in unmatched transactions above threshold

### Manual Notification Testing
```python
# Test notification system
POST /api/notifications/settings/
```

### Generate PDF Reports
```bash
# Current period report
GET /api/export/pdf/

# Specific date range report
GET /api/export/pdf/?start_date=2024-01-01&end_date=2024-01-31
```

## 🛡️ Error Handling

### Notification Failures
- Failed notifications are logged in `NotificationLog` model
- Error messages are captured for debugging
- System continues functioning even if email fails

### PDF Generation Failures
- Graceful error handling with detailed error messages
- Fallback to API error response if PDF generation fails
- Input validation for date parameters

## 📝 Logging and Monitoring

### NotificationLog Model
Tracks all notification attempts:
- `notification_type`: Type of notification sent
- `recipients`: Email addresses notified
- `unmatched_count`: Number of unmatched transactions
- `success`: Whether notification was sent successfully
- `error_message`: Error details if failed
- `timestamp`: When notification was attempted

### Usage Monitoring
- View notification history via API
- Track notification success rates
- Monitor unmatched transaction trends
- Analyze reconciliation performance via PDF reports

## 🔮 Future Enhancements
- Dashboard UI for notification management
- Additional notification channels (Slack, SMS)
- Scheduled report generation
- Enhanced PDF customization options
- Real-time notification websockets 