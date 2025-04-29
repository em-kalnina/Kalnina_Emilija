import hashlib
import sqlite3
import requests
import json

# Izveidot savienojumu ar datubāzi
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Izveido tabulu, ja tā vēl neeksistē
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL)''')

# Izveido tabulu wishlist, ja tā vēl neeksistē
cursor.execute('''CREATE TABLE IF NOT EXISTS wishlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    book_title TEXT NOT NULL,
                    author_name TEXT NOT NULL)''')
conn.commit()

# Funkcija, kas izmanto hashlib SHA256 parolēm
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register():
    username = input("Enter your username: ")
    password = input("Enter your password: ")
    
    # Šifrē paroli ar SHA256
    hashed_password = hash_password(password)
    
    # Ievieto lietotāju datubāzē
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    print("Registration successful!")

def login():
    username = input("Enter your username: ")
    password = input("Enter your password: ")
    
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    if user:
        stored_password = user[2]  # Ņemam glabāto paroli no datubāzes
        if stored_password == hash_password(password):  # Salīdzina ievadīto paroli ar datubāzē esošo
            print("Login successful!")
            return username  # Atgriež lietotājvārdu, ja pieteikšanās ir veiksmīga
        else:
            print("Incorrect password!")
    else:
        print("User not found!")
    return None  # Ja pieteikšanās neizdodas, atgriež None

def search_book():
    query = input("Enter book title to search: ")
    url = f"http://openlibrary.org/search.json?title={query}"
    response = requests.get(url)
    
    if response.status_code == 200:
        books = response.json().get('docs', [])
        if books:
            print("\nFound books:")
            for idx, book in enumerate(books[:5]):  # Limit to first 5 results
                title = book.get('title', 'No title available')
                author = book.get('author_name', ['Unknown'])[0]
                print(f"{idx + 1}. Title: {title}, Author: {author}")
            return books
        else:
            print("No books found.")
            return []
    else:
        print("Error occurred while searching for books.")
        return []

def add_to_wishlist(username, books):
    if not books:
        return
    
    book_choice = int(input(f"Select a book to add to your wishlist (1-{len(books)}): ")) - 1
    if 0 <= book_choice < len(books):
        book = books[book_choice]
        title = book.get('title', 'No title available')
        author = book.get('author_name', ['Unknown'])[0]
        
        # Pievieno grāmatu wishlist
        cursor.execute('INSERT INTO wishlist (username, book_title, author_name) VALUES (?, ?, ?)', 
                       (username, title, author))
        conn.commit()
        print(f"Book '{title}' by {author} added to your wishlist!")
    else:
        print("Invalid choice.")

def view_wishlist(username):
    cursor.execute('SELECT * FROM wishlist WHERE username = ?', (username,))
    wishlist_items = cursor.fetchall()
    
    if wishlist_items:
        print("\nYour Wishlist:")
        for item in wishlist_items:
            print(f"Title: {item[2]}, Author: {item[3]}")
    else:
        print("Your wishlist is empty.")

def main():
    username = None
    while True:
        if username:
            print(f"\nLogged in as {username}")
        else:
            print("\n1. Login")
            print("2. Register")
            print("3. Quit")
            choice = input("Choose an option: ")
            
            if choice == '1':
                username = login()
            elif choice == '2':
                register()
            elif choice == '3':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
                continue
        
        if username:
            print("\n1. Search and add book to wishlist")
            print("2. View wishlist")
            print("3. Logout")
            choice = input("Choose an option: ")

            if choice == '1':
                books = search_book()
                add_to_wishlist(username, books)
            elif choice == '2':
                view_wishlist(username)
            elif choice == '3':
                username = None  # Logout
                print("Logged out successfully!")
            else:
                print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()
