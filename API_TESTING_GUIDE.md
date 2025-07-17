# API Testing Guide - New Features

## 🧪 Testing the Notification System

### 1. Check Notification Settings
```bash
curl -X GET http://localhost:8000/api/notifications/settings/
```

**Expected Response:**
```json
{
    "settings": {
        "UNMATCHED_THRESHOLD": 5,
        "NOTIFY_EMAILS": ["admin@example.com", "finance@example.com"],
        "ENABLE_NOTIFICATIONS": true
    },
    "unmatched_count": 2
}
```

### 2. Test Notification System
```bash
curl -X POST http://localhost:8000/api/notifications/settings/
```

**Expected Response:**
```json
{
    "test_result": {
        "success": false,
        "message": "Unmatched count (2) below threshold (5)"
    },
    "current_unmatched": 2
}
```

### 3. Manually Send Notification
```bash
curl -X POST http://localhost:8000/api/notifications/
```

**Expected Response (if successful):**
```json
{
    "msg": "Notification sent successfully",
    "details": {
        "success": true,
        "message": "Notification sent to 2 recipients",
        "unmatched_count": 5
    }
}
```

### 4. View Notification History
```bash
curl -X GET http://localhost:8000/api/notifications/
```

**Expected Response:**
```json
{
    "notifications": [
        {
            "id": 1,
            "type": "unmatched_transactions",
            "recipients": "admin@example.com,finance@example.com",
            "unmatched_count": 5,
            "total_transactions": 12,
            "timestamp": "2024-01-17T12:30:00Z",
            "success": true,
            "error_message": null
        }
    ],
    "total_count": 1
}
```

## 📄 Testing the PDF Export System

### 1. Generate Current PDF Report
```bash
curl -X GET http://localhost:8000/api/export/pdf/ --output reconciliation_report.pdf
```

### 2. Generate PDF for Date Range
```bash
curl -X GET "http://localhost:8000/api/export/pdf/?start_date=2024-01-01&end_date=2024-01-31" --output reconciliation_report_january.pdf
```

### 3. Check PDF Generation (without downloading)
```bash
curl -I http://localhost:8000/api/export/pdf/
```

**Expected Headers:**
```
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="reconciliation_summary_20240117_1230.pdf"
```

## 🔧 Testing Other Enhanced Endpoints

### 1. Upload CSV with Auto-Notifications
```bash
curl -X POST http://localhost:8000/api/bank/upload/ \
     -F "file=@bank_trans.csv"
```

**Note:** This will now trigger notifications if unmatched transactions exceed threshold.

### 2. Bulk Reconciliation with Notifications
```bash
curl -X POST http://localhost:8000/api/reconciliation/bulk/ \
     -H "Content-Type: application/json" \
     -d '{}'
```

**Note:** This will automatically check and send notifications for any remaining unmatched transactions.

## 🚨 Error Testing Scenarios

### 1. Invalid Date Format in PDF Export
```bash
curl -X GET "http://localhost:8000/api/export/pdf/?start_date=invalid-date"
```

**Expected Response:**
```json
{
    "error": "Invalid start_date format. Use YYYY-MM-DD"
}
```

### 2. Test with Notifications Disabled
Temporarily set `ENABLE_NOTIFICATIONS: False` in settings and test:

```bash
curl -X POST http://localhost:8000/api/notifications/
```

**Expected Response:**
```json
{
    "error": "Failed to send notification",
    "details": {
        "success": false,
        "message": "Notifications are disabled"
    }
}
```

## 🎯 Integration Testing Workflow

### Complete Testing Sequence:

1. **Setup Test Data**
   ```bash
   # Upload some transactions
   curl -X POST http://localhost:8000/api/bank/upload/ -F "file=@bank_trans.csv"
   ```

2. **Check Current Status**
   ```bash
   curl -X GET http://localhost:8000/api/reconciliation/stats/
   ```

3. **Test Notifications**
   ```bash
   curl -X GET http://localhost:8000/api/notifications/settings/
   curl -X POST http://localhost:8000/api/notifications/settings/
   ```

4. **Generate PDF Report**
   ```bash
   curl -X GET http://localhost:8000/api/export/pdf/ --output test_report.pdf
   ```

5. **View Results**
   ```bash
   curl -X GET http://localhost:8000/api/notifications/
   ls -la test_report.pdf
   ```

## 📊 Expected System Behavior

### Notification Triggers:
- ✅ After CSV upload if unmatched count ≥ threshold
- ✅ After bulk reconciliation if unmatched count ≥ threshold  
- ✅ Manual trigger via API
- ✅ Rate limited to prevent spam (max 1 per hour)

### PDF Export Features:
- ✅ Summary statistics table
- ✅ Unmatched transactions listing (first 20)
- ✅ Professional formatting
- ✅ Date range filtering
- ✅ Timestamped filenames

### Error Handling:
- ✅ Graceful email failures (logged but don't break system)
- ✅ PDF generation error handling
- ✅ Input validation for date parameters
- ✅ Proper HTTP status codes

## 🔍 Monitoring & Debugging

### Check Django Logs:
```bash
# In development, check console output for:
# - "Unmatched transactions notification sent to X recipients"
# - "Failed to send unmatched transactions notification: [error]"
```

### Check Admin Panel:
Visit: `http://localhost:8000/admin/reconciliation/notificationlog/`

### Verify Database:
```bash
python manage.py shell
>>> from reconciliation.models import NotificationLog
>>> NotificationLog.objects.all()
``` 