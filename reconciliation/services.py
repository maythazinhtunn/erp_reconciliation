from django.db.models import Q
from .models import BankTransaction, Invoice, Customer, ReconciliationLog, NotificationLog
import re
from decimal import Decimal
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import datetime, timedelta
import logging
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.http import HttpResponse
import io

logger = logging.getLogger(__name__)


class ReconciliationService:
    """
    Service class to handle automatic reconciliation between bank transactions and invoices
    """
    
    @staticmethod
    def process_transaction_reconciliation(transaction):
        """
        Process reconciliation for a single bank transaction
        
        Args:
            transaction: BankTransaction instance
            
        Returns:
            dict: reconciliation result with status and details
        """
        # Find potential invoice matches
        match_result = ReconciliationService._find_matching_invoice_with_confidence(transaction)
        matched_invoice = match_result['invoice']
        confidence = match_result['confidence']
        reason = match_result['reason']
        
        if matched_invoice and confidence >= 0.7:  # Only auto-match if confidence is high enough
            # Match found - mark as paid and update transaction status
            matched_invoice.status = 'paid'
            matched_invoice.save()
            
            transaction.status = 'matched'
            transaction.save()
            
            # Create reconciliation log for the match
            log = ReconciliationLog.objects.create(
                transaction=transaction,
                invoice=matched_invoice,
                matched_by='auto',
                match_reason=reason,
                confidence_score=confidence
            )
            
            return {
                'status': 'matched',
                'invoice_id': matched_invoice.id,
                'match_reason': reason,
                'confidence_score': confidence,
                'log_id': log.id
            }
        else:
            # No match found or low confidence - create unmatched log entry
            log = ReconciliationLog.objects.create(
                transaction=transaction,
                invoice=None,  # No invoice matched
                matched_by='auto',
                match_reason=reason if reason else 'No matching invoice found',
                confidence_score=confidence
            )
            
            return {
                'status': 'unmatched',
                'invoice_id': None,
                'match_reason': reason if reason else 'No matching invoice found',
                'confidence_score': confidence,
                'log_id': log.id
            }
    
    @staticmethod
    def _find_matching_invoice_with_confidence(transaction):
        """
        Find a matching invoice for the given transaction with confidence scoring
        
        Args:
            transaction: BankTransaction instance
            
        Returns:
            dict: {'invoice': Invoice or None, 'confidence': float, 'reason': str}
        """
        best_match = {'invoice': None, 'confidence': 0.0, 'reason': 'No match found'}
        
        # Strategy 1: Exact reference number match in invoice reference_number field
        if transaction.reference_number:
            exact_ref_match = Invoice.objects.filter(
                status='unpaid',
                amount_due=transaction.amount,
                reference_number__iexact=transaction.reference_number
            ).first()
            
            if exact_ref_match:
                return {
                    'invoice': exact_ref_match,
                    'confidence': 1.0,
                    'reason': 'Exact reference number and amount match'
                }
        
        # Strategy 2: Reference number appears in customer name or vice versa
        if transaction.reference_number:
            ref_customer_match = Invoice.objects.filter(
                status='unpaid',
                amount_due=transaction.amount,
                customer__name__icontains=transaction.reference_number
            ).first()
            
            if ref_customer_match:
                confidence = 0.9
                if confidence > best_match['confidence']:
                    best_match = {
                        'invoice': ref_customer_match,
                        'confidence': confidence,
                        'reason': 'Reference number matches customer name and amount matches'
                    }
        
        # Strategy 3: Customer name in transaction description
        potential_customers = ReconciliationService._extract_customer_names_from_description(
            transaction.description
        )
        
        for customer_name in potential_customers:
            matching_invoice = Invoice.objects.filter(
                status='unpaid',
                amount_due=transaction.amount,
                customer__name__icontains=customer_name
            ).first()
            
            if matching_invoice:
                # Calculate confidence based on how well the customer name matches
                name_similarity = ReconciliationService._calculate_name_similarity(
                    customer_name, matching_invoice.customer.name
                )
                confidence = 0.7 + (name_similarity * 0.2)  # Base 0.7 + up to 0.2 for name similarity
                
                if confidence > best_match['confidence']:
                    best_match = {
                        'invoice': matching_invoice,
                        'confidence': confidence,
                        'reason': f'Customer name "{customer_name}" found in description, amount matches'
                    }
        
        # Strategy 4: Partial customer name matching (lower confidence)
        all_customers = Customer.objects.all()
        
        for customer in all_customers:
            if (ReconciliationService._is_customer_mentioned(customer.name, transaction.description) or 
                ReconciliationService._is_customer_mentioned(customer.name, transaction.reference_number)):
                
                matching_invoice = Invoice.objects.filter(
                    status='unpaid',
                    amount_due=transaction.amount,
                    customer=customer
                ).first()
                
                if matching_invoice:
                    confidence = 0.6  # Lower confidence for partial matches
                    
                    if confidence > best_match['confidence']:
                        best_match = {
                            'invoice': matching_invoice,
                            'confidence': confidence,
                            'reason': f'Partial customer name match for "{customer.name}", amount matches'
                        }
        
        # Strategy 5: Amount-only match (very low confidence, requires manual review)
        if best_match['confidence'] == 0.0:
            amount_only_match = Invoice.objects.filter(
                status='unpaid',
                amount_due=transaction.amount
            ).first()
            
            if amount_only_match:
                best_match = {
                    'invoice': amount_only_match,
                    'confidence': 0.3,
                    'reason': 'Amount-only match - requires manual verification'
                }
        
        return best_match
    
    @staticmethod
    def _calculate_name_similarity(name1, name2):
        """
        Calculate similarity between two names (simple implementation)
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            float: Similarity score between 0 and 1
        """
        if not name1 or not name2:
            return 0.0
        
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # Exact match
        if name1_lower == name2_lower:
            return 1.0
        
        # One contains the other
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return 0.8
        
        # Word overlap
        words1 = set(name1_lower.split())
        words2 = set(name2_lower.split())
        
        if words1 and words2:
            overlap = len(words1.intersection(words2))
            union = len(words1.union(words2))
            return overlap / union if union > 0 else 0.0
        
        return 0.0
    
    @staticmethod
    def _extract_customer_names_from_description(description):
        """
        Extract potential customer names from transaction description
        
        Args:
            description: Transaction description string
            
        Returns:
            list: List of potential customer names
        """
        if not description:
            return []
        
        # Split description into words and filter out common banking terms
        words = re.findall(r'\b[A-Za-z]{2,}\b', description)
        
        # Filter out common banking terms
        banking_terms = {
            'payment', 'from', 'to', 'transfer', 'bank', 'transaction', 
            'ref', 'reference', 'deposit', 'withdrawal', 'fee', 'charge',
            'via', 'online', 'mobile', 'app', 'card', 'cash', 'check'
        }
        
        potential_names = []
        
        # Single words that could be names
        for word in words:
            if word.lower() not in banking_terms and len(word) >= 2:
                potential_names.append(word)
        
        # Two-word combinations that could be full names
        for i in range(len(words) - 1):
            if (words[i].lower() not in banking_terms and 
                words[i+1].lower() not in banking_terms and
                len(words[i]) >= 2 and len(words[i+1]) >= 2):
                potential_names.append(f"{words[i]} {words[i+1]}")
        
        return potential_names
    
    @staticmethod
    def _is_customer_mentioned(customer_name, text):
        """
        Check if customer name is mentioned in the given text
        
        Args:
            customer_name: Customer name to search for
            text: Text to search in
            
        Returns:
            bool: True if customer name is found
        """
        if not text or not customer_name:
            return False
        
        # Case-insensitive partial match
        return customer_name.lower() in text.lower()
    
    @staticmethod
    def bulk_reconcile_transactions(transactions=None):
        """
        Perform bulk reconciliation on multiple transactions
        
        Args:
            transactions: QuerySet of BankTransaction objects. If None, processes all unmatched transactions
            
        Returns:
            dict: Summary of reconciliation results
        """
        if transactions is None:
            transactions = BankTransaction.objects.filter(status='unmatched')
        
        results = {
            'total_processed': 0,
            'matched': 0,
            'unmatched': 0,
            'high_confidence_matches': 0,
            'low_confidence_matches': 0,
            'details': []
        }
        
        for transaction in transactions:
            result = ReconciliationService.process_transaction_reconciliation(transaction)
            
            results['total_processed'] += 1
            if result['status'] == 'matched':
                results['matched'] += 1
                if result['confidence_score'] >= 0.8:
                    results['high_confidence_matches'] += 1
                else:
                    results['low_confidence_matches'] += 1
            else:
                results['unmatched'] += 1
            
            results['details'].append({
                'transaction_id': transaction.id,
                'amount': str(transaction.amount),
                'description': transaction.description,
                'reference_number': transaction.reference_number,
                'result': result
            })
        
        # Check for unmatched transactions and send notification if needed
        if results['unmatched'] > 0:
            NotificationService.check_and_send_unmatched_notification()
        
        return results


class NotificationService:
    """
    Service class to handle notifications for reconciliation events
    """
    
    @staticmethod
    def send_unmatched_transactions_notification(unmatched_transactions=None):
        """
        Send email notification for unmatched transactions
        
        Args:
            unmatched_transactions: QuerySet of unmatched transactions. If None, fetches all unmatched
            
        Returns:
            dict: Result of the notification attempt
        """
        if not getattr(settings, 'NOTIFICATION_SETTINGS', {}).get('ENABLE_NOTIFICATIONS', False):
            return {'success': False, 'message': 'Notifications are disabled'}
        
        if unmatched_transactions is None:
            unmatched_transactions = BankTransaction.objects.filter(status='unmatched')
        
        unmatched_count = unmatched_transactions.count()
        threshold = settings.NOTIFICATION_SETTINGS.get('UNMATCHED_THRESHOLD', 5)
        
        if unmatched_count < threshold:
            return {'success': False, 'message': f'Unmatched count ({unmatched_count}) below threshold ({threshold})'}
        
        notify_emails = settings.NOTIFICATION_SETTINGS.get('NOTIFY_EMAILS', [])
        if not notify_emails:
            return {'success': False, 'message': 'No notification emails configured'}
        
        # Prepare email context
        total_transactions = BankTransaction.objects.count()
        total_amount_unmatched = sum(float(t.amount) for t in unmatched_transactions)
        
        context = {
            'unmatched_count': unmatched_count,
            'total_transactions': total_transactions,
            'total_amount_unmatched': total_amount_unmatched,
            'threshold': threshold,
            'transactions': unmatched_transactions[:10],  # Show first 10 in email
            'timestamp': timezone.now(),
        }
        
        subject = f'ERP Alert: {unmatched_count} Unmatched Transactions Require Attention'
        
        # Create email message
        message = f"""
ERP Reconciliation Alert

Dear Finance Team,

We have detected {unmatched_count} unmatched bank transactions that require your attention.

Summary:
- Total Unmatched Transactions: {unmatched_count}
- Total Transaction Amount Unmatched: ${total_amount_unmatched:,.2f}
- Total Transactions in System: {total_transactions}
- Alert Threshold: {threshold} transactions

Recent Unmatched Transactions:
"""
        
        for i, transaction in enumerate(unmatched_transactions[:5], 1):
            message += f"""
{i}. Transaction ID: {transaction.id}
   Date: {transaction.date}
   Amount: ${transaction.amount}
   Description: {transaction.description}
   Reference: {transaction.reference_number}
"""
        
        message += f"""

Please review these transactions in the ERP system and perform manual matching if necessary.

System generated at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Best regards,
ERP Reconciliation System
"""
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                notify_emails,
                fail_silently=False,
            )
            
            # Log the notification
            NotificationLog.objects.create(
                notification_type='unmatched_transactions',
                recipients=','.join(notify_emails),
                unmatched_count=unmatched_count,
                total_transactions=total_transactions,
                success=True
            )
            
            logger.info(f"Unmatched transactions notification sent to {len(notify_emails)} recipients")
            return {
                'success': True, 
                'message': f'Notification sent to {len(notify_emails)} recipients',
                'unmatched_count': unmatched_count
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Log the failed notification
            NotificationLog.objects.create(
                notification_type='unmatched_transactions',
                recipients=','.join(notify_emails),
                unmatched_count=unmatched_count,
                total_transactions=total_transactions,
                success=False,
                error_message=error_msg
            )
            
            logger.error(f"Failed to send unmatched transactions notification: {error_msg}")
            return {'success': False, 'message': f'Failed to send notification: {error_msg}'}
    
    @staticmethod
    def check_and_send_unmatched_notification():
        """
        Check if notification should be sent based on current unmatched transactions
        
        Returns:
            dict: Result of the notification check and attempt
        """
        # Don't send notifications more than once per hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_notification = NotificationLog.objects.filter(
            notification_type='unmatched_transactions',
            timestamp__gte=one_hour_ago,
            success=True
        ).exists()
        
        if recent_notification:
            return {'success': False, 'message': 'Notification already sent within the last hour'}
        
        return NotificationService.send_unmatched_transactions_notification()


class PDFExportService:
    """
    Service class to handle PDF export of reconciliation summaries
    """
    
    @staticmethod
    def generate_reconciliation_summary_pdf(start_date=None, end_date=None):
        """
        Generate a PDF report of reconciliation summary
        
        Args:
            start_date: Start date for the report (optional)
            end_date: End date for the report (optional)
            
        Returns:
            HttpResponse: PDF file response
        """
        # Create a file-like buffer to receive PDF data
        buffer = io.BytesIO()
        
        # Create the PDF object, using the buffer as its "file"
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Add title
        title = Paragraph("ERP Reconciliation Summary Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Add report date range
        date_range_text = "Report Generated: " + timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        if start_date and end_date:
            date_range_text += f"<br/>Period: {start_date} to {end_date}"
        date_range = Paragraph(date_range_text, styles['Normal'])
        elements.append(date_range)
        elements.append(Spacer(1, 20))
        
        # Filter data based on date range if provided
        transactions_query = BankTransaction.objects.all()
        logs_query = ReconciliationLog.objects.all().select_related('transaction', 'invoice')
        
        if start_date and end_date:
            transactions_query = transactions_query.filter(date__range=[start_date, end_date])
            logs_query = logs_query.filter(timestamp__date__range=[start_date, end_date])
        
        # Summary Statistics
        total_transactions = transactions_query.count()
        matched_transactions = transactions_query.filter(status='matched').count()
        unmatched_transactions = transactions_query.filter(status='unmatched').count()
        
        total_invoices = Invoice.objects.count()
        paid_invoices = Invoice.objects.filter(status='paid').count()
        unpaid_invoices = Invoice.objects.filter(status='unpaid').count()
        
        auto_matches = logs_query.filter(matched_by='auto').count()
        manual_matches = logs_query.filter(matched_by='manual').count()
        
        # Summary table
        summary_data = [
            ['Metric', 'Count', 'Percentage'],
            ['Total Transactions', str(total_transactions), '100%'],
            ['Matched Transactions', str(matched_transactions), 
             f'{(matched_transactions/total_transactions*100):.1f}%' if total_transactions > 0 else '0%'],
            ['Unmatched Transactions', str(unmatched_transactions), 
             f'{(unmatched_transactions/total_transactions*100):.1f}%' if total_transactions > 0 else '0%'],
            ['', '', ''],
            ['Total Invoices', str(total_invoices), '100%'],
            ['Paid Invoices', str(paid_invoices), 
             f'{(paid_invoices/total_invoices*100):.1f}%' if total_invoices > 0 else '0%'],
            ['Unpaid Invoices', str(unpaid_invoices), 
             f'{(unpaid_invoices/total_invoices*100):.1f}%' if total_invoices > 0 else '0%'],
            ['', '', ''],
            ['Auto Matches', str(auto_matches), ''],
            ['Manual Matches', str(manual_matches), ''],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 1*inch, 1*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(Paragraph("Summary Statistics", styles['Heading2']))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Unmatched Transactions Details
        if unmatched_transactions > 0:
            elements.append(Paragraph("Unmatched Transactions", styles['Heading2']))
            
            unmatched_list = transactions_query.filter(status='unmatched')[:20]  # Limit to first 20
            unmatched_data = [['ID', 'Date', 'Amount', 'Description', 'Reference']]
            
            for transaction in unmatched_list:
                unmatched_data.append([
                    str(transaction.id),
                    str(transaction.date),
                    f'${transaction.amount}',
                    transaction.description[:50] + '...' if len(transaction.description) > 50 else transaction.description,
                    transaction.reference_number
                ])
            
            unmatched_table = Table(unmatched_data, colWidths=[0.5*inch, 1*inch, 1*inch, 2.5*inch, 1*inch])
            unmatched_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(unmatched_table)
            
            if unmatched_transactions > 20:
                elements.append(Spacer(1, 12))
                elements.append(Paragraph(f"... and {unmatched_transactions - 20} more unmatched transactions", styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        
        # Get the value of the BytesIO buffer and write it to the response
        pdf = buffer.getvalue()
        buffer.close()
        
        # Create HTTP response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reconciliation_summary_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        response.write(pdf)
        
        return response 