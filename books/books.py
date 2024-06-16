import requests
import os
from flask import Flask, request, jsonify
from flask_restful import Api
from pymongo import MongoClient

app = Flask(__name__)
api = Api(app)

# Initialize MongoDB client
mongo_host = os.getenv('MONGO_HOST', 'mongodb')
mongo_port = int(os.getenv('MONGO_PORT', 27017))
client = MongoClient(f'mongodb://{mongo_host}:{mongo_port}')

# Access the database and collections
db = client.bookstore
books_collection = db.books
ratings_collection = db.ratings

@app.route('/books', methods=['GET', 'POST'])
def handle_books():
    if request.method == 'GET':
        # Extract all possible query parameters
        query = {}
        title = request.args.get('title')
        authors = request.args.get('authors')
        isbn = request.args.get('ISBN')
        publisher = request.args.get('publisher')
        publisheddate = request.args.get('publishedDate')
        genre = request.args.get('genre')

        if title:
            query['title'] = {'$regex': title, '$options': 'i'}
        if authors:
            query['authors'] = {'$regex': authors, '$options': 'i'}
        if isbn:
            query['ISBN'] = isbn
        if publisher:
            query['publisher'] = {'$regex': publisher, '$options': 'i'}
        if publisheddate:
            query['publishedDate'] = publisheddate
        if genre:
            if genre not in ["Fiction", "Children", "Biography", "Science", "Science Fiction", "Fantasy", "Other"]:
                return jsonify({"error": "Invalid genre value"}), 422
            query['genre'] = genre

        filtered_books = list(books_collection.find(query))
        return jsonify(filtered_books)

    elif request.method == 'POST':
        data = request.json

        # Check if all required fields are present
        required_fields = ['title', 'ISBN', 'genre']
        if not data or not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 422

        # Check if the genre provided is one of the accepted values
        accepted_genres = ["Fiction", "Non-fiction", "Science Fiction", "Fantasy", "Romance", "Mystery", "Thriller",
                           "Horror", "Poetry", "Biography", "Autobiography", "Historical Fiction", "Crime", "Adventure",
                           "Western", "Humor", "Satire", "Drama", "Action", "Children's", "Young Adult", "Self-help",
                           "Philosophy", "Science", "Technology", "Engineering", "Mathematics", "Business", "Finance",
                           "Economics", "Politics", "History", "Art", "Music", "Film", "Sports", "Cooking", "Travel",
                           "Religion", "Spirituality", "Health", "Fitness", "Psychology", "Education", "Reference",
                           "Comics", "Graphic Novel", "Anthology", "Short Stories", "Essays", "Literary Criticism",
                           "Journalism", "Memoir", "True Crime", "Encyclopedia", "Dictionaries", "Textbooks", "Manuals",
                           "Guides", "Directories"]
        if data['genre'] not in accepted_genres:
            return jsonify({"error": "Invalid genre"}), 422

        # Check if there's already a book with the provided ISBN in the collection
        existing = books_collection.find_one({'ISBN': data['ISBN']})
        if existing:
            return jsonify({"error": "Book with given ISBN already exists"}), 422

        # Check if there's any discrepancy between user-provided data and data from APIs
        try:
            google_data = get_google_book_data(data['ISBN'])
        except Exception as e:
            return jsonify({"error": f"Error connecting to Google Books API: {e}"}), 500

        book = {
            'title': data['title'],
            'authors': google_data['authors'],
            'ISBN': data['ISBN'],
            'publisher': google_data['publisher'],
            'publishedDate': google_data['publishedDate'],
            'genre': data['genre'],
        }

        books_collection.insert_one(book)

        rating = {
            'values': [],
            'average': 0,
            'title': data['title'],
            'book_id': book['_id']
        }
        ratings_collection.insert_one(rating)
        update_top_books()

        return jsonify({"id": str(book['_id'])}), 201


@app.route('/books/<id>', methods=['GET', 'PUT', 'DELETE'])
def handle_book(id):
    from bson.objectid import ObjectId # type: ignore
    book = books_collection.find_one({'_id': ObjectId(id)})
    if not book:
        return jsonify({"error": "Book not found"}), 404

    if request.method == 'GET':
        return jsonify(book)
  
    if request.method == 'PUT':
        data = request.json
        if not data:
            return jsonify({"error": "No book data provided"}), 415

        # Check if all required fields are provided
        required_fields = ['title', 'authors', 'ISBN', 'publisher', 'publishedDate', 'genre']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 422

        # Check if the genre provided is one of the accepted values
        accepted_genres = ["Fiction", "Non-fiction", "Science Fiction", "Fantasy", "Romance", "Mystery",
                           "Thriller", "Horror", "Poetry", "Biography", "Autobiography", "Historical Fiction", "Crime",
                           "Adventure", "Western", "Humor", "Satire", "Drama", "Action", "Children's", "Young Adult",
                           "Self-help", "Philosophy", "Science", "Technology", "Engineering", "Mathematics", "Business",
                           "Finance", "Economics", "Politics", "History", "Art", "Music", "Film", "Sports", "Cooking",
                           "Travel", "Religion", "Spirituality", "Health", "Fitness", "Psychology", "Education",
                           "Reference", "Comics", "Graphic Novel", "Anthology", "Short Stories", "Essays",
                           "Literary Criticism", "Journalism", "Memoir", "True Crime", "Encyclopedia", "Dictionaries",
                           "Textbooks", "Manuals", "Guides", "Directories"]
        if data['genre'] not in accepted_genres:
            return jsonify({"error": "Invalid genre"}), 422
    
        books_collection.update_one({'_id': ObjectId(id)}, {'$set': data})
        return jsonify(data)

    if request.method == 'DELETE':
        books_collection.delete_one({'_id': ObjectId(id)})
        ratings_collection.delete_one({'book_id': ObjectId(id)})
        update_top_books()
        return jsonify({"id": id}), 200


@app.route('/ratings', methods=['GET'])
def handle_ratings():
    book_id = request.args.get('id')
    if book_id:
        rating = ratings_collection.find_one({'book_id': book_id})
        if not rating:
            return jsonify({"error": "Rating not found"}), 404
        return jsonify(rating)
    else:
        return jsonify(list(ratings_collection.find()))


@app.route('/ratings/<id>', methods=['GET'])
def handle_rating(id):
    from bson.objectid import ObjectId
    rating = ratings_collection.find_one({'book_id': ObjectId(id)})
    if not rating:
        return jsonify({"error": "Rating not found"}), 404
    return jsonify(rating)


@app.route('/ratings/<id>/values', methods=['POST'])
def add_rating(id):
    from bson.objectid import ObjectId
    data = request.json
    if not data or 'value' not in data or data['value'] not in [1, 2, 3, 4, 5]:
        return jsonify({"error": "Invalid rating value"}), 422

    rating = ratings_collection.find_one({'book_id': ObjectId(id)})
    if not rating:
        return jsonify({"error": "Rating not found"}), 404

    rating['values'].append(data['value'])
    rating['average'] = sum(rating['values']) / len(rating['values'])

    ratings_collection.update_one({'book_id': ObjectId(id)}, {'$set': rating})
    update_top_books()

    return jsonify(rating['average'])


@app.route('/top', methods=['GET'])
def get_top_books():
    return jsonify(top_books)


def get_google_book_data(isbn):
    url = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}'
    response = requests.get(url)
    data = response.json()['items'][0]['volumeInfo']
    return {
        'title': data.get('title', 'missing'),
        'authors': get_authors_string(data.get('authors')),
        'publisher': data.get('publisher', 'missing'),
        'publishedDate': data.get('publishedDate', 'missing')
    }


def get_authors_string(authors):
    if not authors:
        return 'missing'
    elif len(authors) == 1:
        return authors[0]
    else:
        return ' and '.join(authors)


def update_top_books():
    # Filter books with at least 3 ratings
    filtered_ratings = list(ratings_collection.find({'values': {'$size': {'$gte': 3}}}))

    # Sort the filtered ratings dictionary by average rating in descending order
    sorted_ratings = sorted(filtered_ratings, key=lambda x: x['average'], reverse=True)

    # Update the global variable top_books with the selected top 3 books
    global top_books
    top_books = sorted_ratings[:3]

    # Check if there are more than 3 ratings and if there are books with the same rating as the 3rd book
    if len(filtered_ratings) > 3:
        lowest_top_rating = top_books[-1]['average']
        additional_books = [rating for rating in filtered_ratings if rating['average'] == lowest_top_rating and rating not in top_books]

        # Extend top_books with additional books, up to a total of 3
        top_books.extend(additional_books)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=int(os.getenv('PORT', 80)))
