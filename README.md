# ERP Reconciliation System

A sophisticated Django-based ERP reconciliation system that automatically matches bank transactions with invoices using multiple matching strategies and confidence scoring.

## 🌟 Features

### Core Functionality
- **Automatic Bank Transaction Reconciliation**: Smart matching of bank transactions with open invoices
- **Multiple Matching Strategies**: 
  - Reference number matching (exact)
  - Customer name + amount matching
  - Partial name matching with confidence scoring
  - Amount-only matching for fallback scenarios
- **Confidence Scoring**: Advanced scoring system (0.0 to 1.0) for match quality assessment
- **Real-time Status Updates**: Automatic status updates for matched transactions and invoices

### Advanced Features
- **Notification System**: Automated alerts for unmatched transactions above configurable thresholds
- **PDF Export**: Generate detailed reconciliation reports
- **Bulk Operations**: Process multiple transactions simultaneously
- **Comprehensive Logging**: Detailed audit trail for all reconciliation activities
- **REST API**: Full API coverage for integration with external systems

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL
- pip and virtualenv

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd erp_reconciliation
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database setup**
   ```bash
   # Configure PostgreSQL database in erp_project/settings.py
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Load sample data**
   ```bash
   python manage.py populate_sample_data --clear
   ```

7. **Run the server**
   ```bash
   python manage.py runserver
   ```

Visit `http://localhost:8000` to access the application.

## 💻 Usage

### Management Commands

**Populate sample data:**
```bash
python manage.py populate_sample_data --clear
```

**Test reconciliation:**
```bash
python manage.py test_reconciliation --bulk
```

**Add invoice:**
```bash
python manage.py add_invoice \
  --customer-name "TechStart Inc" \
  --customer-email "accounts@techstart.com" \
  --amount "2500.00" \
  --reference "INV-008"
```



### CSV Upload Format

Upload bank transactions via CSV with the following format:
```csv
date,description,amount,reference_number
2024-01-15,Payment from ABC Corp,1500.00,REF123
2024-01-16,Transfer from XYZ Ltd,2500.00,PAY456
```

## 🔗 API Documentation

### Core Endpoints

#### Bank Transactions
- `POST /bank/upload/` - Upload CSV with automatic reconciliation
- `GET /bank/unmatched/` - Get unmatched transactions
- `POST /bank/match/` - Manual transaction matching

#### Reconciliation
- `POST /reconciliation/bulk/` - Bulk reconciliation of unmatched transactions
- `POST /reconciliation/reprocess/` - Reprocess a specific transaction
- `GET /reconciliation/logs/` - Get reconciliation logs
- `GET /reconciliation/stats/` - Get reconciliation statistics

#### Notifications
- `GET /api/notifications/settings/` - Get notification settings
- `POST /api/notifications/settings/` - Test notification system
- `POST /api/notifications/` - Manually send notifications

### Example API Calls

**Upload bank transactions:**
```bash
curl -X POST http://localhost:8000/bank/upload/ \
  -F "file=@bank_trans.csv"
```

**Get reconciliation statistics:**
```bash
curl -X GET http://localhost:8000/reconciliation/stats/
```

**Manual transaction matching:**
```bash
curl -X POST http://localhost:8000/bank/match/ \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": 1, "invoice_id": 2}'
```

For detailed API testing examples, see [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md).

## 📊 Reconciliation Process

### Matching Logic Priority
1. **Reference Number Match** (Confidence: 1.0)
   - Exact match between transaction reference and invoice reference
2. **Customer Name + Amount** (Confidence: 0.85-0.95)
   - Customer name found in transaction description with exact amount
3. **Partial Name Match** (Confidence: 0.75-0.90)
   - Partial customer name matches with confidence scoring
4. **Amount Only** (Confidence: 0.50-0.70)
   - Low confidence matching based on amount alone

### Status Updates
- **Matched transactions**: Status set to 'matched'
- **Matched invoices**: Status automatically updated to 'Paid'
- **Audit trail**: Complete reconciliation log for every transaction

## 🛠️ Technology Stack

- **Backend**: Django 5.2.4, Django REST Framework 3.16.0
- **Database**: PostgreSQL (psycopg2-binary)
- **Data Processing**: pandas 2.3.1, numpy 2.3.1
- **File Processing**: openpyxl 3.1.5
- **PDF Generation**: reportlab 4.4.2
- **Image Processing**: Pillow 11.3.0

## 📁 Project Structure

```
erp_reconciliation/
├── erp_project/           # Django project settings
├── reconciliation/        # Main reconciliation app
│   ├── models.py         # Database models
│   ├── views.py          # API views
│   ├── services.py       # Business logic
│   ├── serializers.py    # API serializers
│   ├── management/       # Custom management commands
│   ├── static/           # Static files
│   └── templates/        # HTML templates
├── requirements.txt      # Python dependencies
├── manage.py            # Django management script
└── README.md           # This file
```

## 🧪 Testing

The system includes comprehensive test coverage with sample data:

**Test Results Summary:**
- Successfully matches 6 out of 8 test transactions
- Perfect matches: 2 transactions (confidence: 1.0)
- Customer name matches: 4 transactions (confidence: 0.86-0.90)
- Unmatched: 2 transactions (manual review required)

Run tests:
```bash
python manage.py test
```

Demo the system:
```bash
python demo_new_features.py
```

## 📋 Configuration

### Notification Settings
Configure in `erp_project/settings.py`:
```python
NOTIFICATION_SETTINGS = {
    'UNMATCHED_THRESHOLD': 5,
    'NOTIFY_EMAILS': ['admin@example.com', 'finance@example.com'],
    'ENABLE_NOTIFICATIONS': True,
}
```

### Database Configuration
Update database settings in `erp_project/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 📚 Additional Documentation

- [API Testing Guide](API_TESTING_GUIDE.md) - Comprehensive API testing examples
- [Reconciliation Features](RECONCILIATION_FEATURES.md) - Detailed feature documentation
- [Implementation Details](README_RECONCILIATION.md) - Technical implementation notes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check existing documentation in the `docs/` folder
- Review the API testing guide for troubleshooting

## 🔄 Version History

- **v1.0** - Initial release with core reconciliation features
- **v1.1** - Added notification system and PDF export
- **v1.2** - Enhanced matching algorithms and confidence scoring
- **Current** - Bulk operations and advanced API endpoints 