import ofxparse
from rapidfuzz import process

def deduplicate_and_parse_ofx(file_path):
    with open(file_path, 'r') as file:
        ofx = ofxparse.OfxParser.parse(file)
    
    transactions = []
    for account in ofx.accounts:
        for transaction in account.statement.transactions:
            transactions.append({
                "id": transaction.id,
                "date": transaction.date,
                "amount": transaction.amount,
                "description": transaction.payee
            })
    
    # Deduplicate based on a unique identifier, e.g., 'id'
    deduplicated_transactions = []
    seen_ids = set()
    for transaction in transactions:
        if transaction['id'] not in seen_ids:
            deduplicated_transactions.append(transaction)
            seen_ids.add(transaction['id'])
    
    return deduplicated_transactions

def parse_ofx(file_path):
    transactions = deduplicate_and_parse_ofx(file_path)
    
    # Example: Extract useful information
    parsed_transactions = []
    for transaction in transactions:
        parsed_transaction = {
            "id": transaction['id'],
            "date": transaction['date'],
            "amount": transaction['amount'],
            "description": transaction['description']
        }
        parsed_transactions.append(parsed_transaction)
    
    return parsed_transactions
