import sqlite3
import bcrypt
import requests

# Book Class
class Book:
    def __init__(self, title, author, genre=None):
        self.title = title
        self.author = author
        self.genre = genre

    def __str__(self):
        return f"Title: {self.title}, Author: {self.author}, Genre: {self.genre}"

# Wishlist Class (Database operations)
class Wishlist:
    def __init__(self, db_name='wishlist.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Create tables for users, wishlist, genres, and reviews
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT NOT NULL UNIQUE,
                                password TEXT NOT NULL)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS wishlist (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                book_title TEXT NOT NULL,
                                author_name TEXT NOT NULL,
                                genre TEXT,
                                FOREIGN KEY(user_id) REFERENCES users(id))''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS genres (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                book_title TEXT NOT NULL,
                                review TEXT,
                                FOREIGN KEY(user_id) REFERENCES users(id))''')
        self.conn.commit()

    def add_user(self, username, password):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        self.conn.commit()

    def authenticate_user(self, username, password):
        self.cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
        result = self.cursor.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0]):
            return True
        return False

    def add_book(self, user_id, book):
        self.cursor.execute('INSERT INTO wishlist (user_id, book_title, author_name, genre) VALUES (?, ?, ?, ?)', 
                            (user_id, book.title, book.author, book.genre))
        self.conn.commit()

    def add_review(self, user_id, book_title, review):
        self.cursor.execute('INSERT INTO reviews (user_id, book_title, review) VALUES (?, ?, ?)', 
                            (user_id, book_title, review))
        self.conn.commit()

    def view_wishlist(self, user_id):
        self.cursor.execute('SELECT * FROM wishlist WHERE user_id = ?', (user_id,))
        wishlist_items = self.cursor.fetchall()
        if wishlist_items:
            for item in wishlist_items:
                print(f"Title: {item[2]}, Author: {item[3]}, Genre: {item[4]}")
        else:
            print("Your wishlist is empty.")

    def view_reviews(self, book_title):
        self.cursor.execute('''
            SELECT u.username, r.review 
            FROM reviews r 
            JOIN users u ON r.user_id = u.id 
            WHERE r.book_title = ?
        ''', (book_title,))
        reviews = self.cursor.fetchall()
        if reviews:
            print(f"\nAtsauksmes par grāmatu: {book_title}")
            for username, review in reviews:
                print(f"- {username}: {review}")
        else:
            print("Par šo grāmatu vēl nav atsauksmju.")

# Library Class for interacting with the Open Library API
class Library:
    @staticmethod
    def search_books_by_author(author):
        url = f"http://openlibrary.org/search.json?author={author}"
        response = requests.get(url)
        if response.status_code == 200:
            books = response.json().get('docs', [])
            return [Book(book.get('title', 'No title available'), 
                         book.get('author_name', ['Unknown'])[0]) for book in books]
        else:
            print("Error occurred while searching for books.")
            return []

# Main function
def main():
    wishlist = Wishlist()

    # User login and registration
    print("Welcome to the Book Wishlist Manager!")
    while True:
        print("\n1. Register")
        print("2. Login")
        print("3. Quit")
        action = input("Choose an option: ")

        if action == '1':
            username = input("Enter your username: ")
            password = input("Enter your password: ")
            wishlist.add_user(username, password)
            print(f"User {username} registered successfully!")

        elif action == '2':
            username = input("Enter your username: ")
            password = input("Enter your password: ")
            if wishlist.authenticate_user(username, password):
                print(f"Welcome back, {username}!")
                user_id = wishlist.cursor.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()[0]
                
                while True:
                    print("\n1. Search and add book to wishlist")
                    print("2. View wishlist")
                    print("3. Add a review")
                    print("4. See reviews")
                    print("5. Logout")
                    choice = input("Choose an option: ")

                    if choice == '1':
                        author = input("Enter the author's name: ")
                        books = Library.search_books_by_author(author)
                        if books:
                            for idx, book in enumerate(books):
                                print(f"{idx + 1}. {book}")
                            book_choice = int(input(f"Select a book to add to your wishlist (1-{len(books)}): ")) - 1
                            if 0 <= book_choice < len(books):
                                wishlist.add_book(user_id, books[book_choice])
                                print(f"Book '{books[book_choice].title}' by {books[book_choice].author} added to your wishlist!")
                            else:
                                print("Invalid choice.")

                    elif choice == '2':
                        wishlist.view_wishlist(user_id)

                    elif choice == '3':
                        book_title = input("Enter the title of the book you want to review: ")
                        review = input("Enter your review: ")
                        wishlist.add_review(user_id, book_title, review)
                        print(f"Review for '{book_title}' added!")

                    elif choice == '4':
                        book_title = input("Enter the title of the book you want to read reviews about: ")
                        wishlist.view_reviews(book_title)

                    elif choice == '5':
                        print("Logging out...")
                        break

                    else:
                        print("Invalid option, please try again.")

            else:
                print("Invalid credentials, please try again.")
        
        elif action == '3':
            print("Goodbye!")
            break
        
        else:
            print("Invalid option, please try again.")

if __name__ == '__main__':
    main()
