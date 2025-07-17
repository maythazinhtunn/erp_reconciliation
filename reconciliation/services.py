from django.db.models import Q
from .models import BankTransaction, Invoice, Customer, ReconciliationLog
import re
from decimal import Decimal


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
        
        return results 