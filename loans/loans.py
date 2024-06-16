import requests
import os
import uuid
from flask import Flask, request, jsonify
from flask_restful import Api
from pymongo import MongoClient

app = Flask(__name__)
api = Api(app)

# Get the MongoDB URL from the environment variable
mongo_url = os.getenv('MONGO_URL', 'mongodb://mongo:27017/LoansDB')
client = MongoClient(mongo_url)
db = client.get_default_database()  # This will get the database specified in the URL
loans_collection = db.loans

@app.route('/loans', methods=['GET', 'POST'])
def handle_loans():
    if request.method == 'GET':
        member_name = request.args.get('memberName')
        isbn = request.args.get('ISBN')
        loan_date = request.args.get('loanDate')

        query = {}
        if member_name:
            query['memberName'] = member_name
        if isbn:
            query['ISBN'] = isbn
        if loan_date:
            query['loanDate'] = loan_date

        filtered_loans = list(loans_collection.find(query))

        return jsonify(filtered_loans), 200

    elif request.method == 'POST':
        data = request.json

        if not data:
            return jsonify({"error": "JSON content not supplied"}), 415

        if not all(field in data for field in ['memberName', 'ISBN', 'loanDate']):
            return jsonify({"error": "Missing required fields"}), 422

        member_loans = list(loans_collection.find({'memberName': data['memberName']}))
        if len(member_loans) >= 2:
            return jsonify({"error": "Member already has 2 or more books on loan"}), 422

        book_on_loan = loans_collection.find_one({'ISBN': data['ISBN']})
        if book_on_loan:
            return jsonify({"error": "Book is already on loan"}), 422

        try:
            book_data = get_book_data(data['ISBN'])
        except Exception as e:
            return jsonify({"error": str(e)}), 422

        loan = {
            "memberName": data['memberName'],
            "ISBN": data['ISBN'],
            "title": book_data['title'],
            "bookID": book_data['id'],
            "loanDate": data['loanDate'],
            "loanID": str(uuid.uuid4())
        }

        loans_collection.insert_one(loan)
        return jsonify({"loanID": loan['loanID']}), 201

@app.route('/loans/<loanID>', methods=['GET', 'DELETE'])
def handle_loan(loanID):
    loan = loans_collection.find_one({'loanID': loanID})
    if not loan:
        return jsonify({"error": "Loan not found"}), 404

    if request.method == 'GET':
        return jsonify(loan), 200

    elif request.method == 'DELETE':
        loans_collection.delete_one({'loanID': loanID})
        return jsonify({"loanID": loanID}), 200

def get_book_data(isbn):
    books_service_url = 'http://books-service:5001/books'
    response = requests.get(f'{books_service_url}?ISBN={isbn}')
    if response.status_code != 200:
        raise Exception("Failed to retrieve book data")

    books = response.json()
    if not books:
        raise Exception("Book not found")

    return books[0]

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=int(os.getenv('PORT', 80)))