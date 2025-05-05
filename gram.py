import sqlite3
import bcrypt
import requests
import tkinter as tk
from tkinter import messagebox

class Book:
    def __init__(self, title, author):
        self.title = title
        self.author = author

    def __str__(self):
        return f"Nosaukums: {self.title}, Autors: {self.author}"

class Wishlist:
    def __init__(self, db_name='wishlist.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT NOT NULL UNIQUE,
                                password TEXT NOT NULL)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS wishlist (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                book_title TEXT NOT NULL,
                                author_name TEXT NOT NULL,
                                FOREIGN KEY(user_id) REFERENCES users(id))''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                book_title TEXT NOT NULL,
                                author_name TEXT NOT NULL,
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

    def get_user_id(self, username):
        self.cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_book(self, user_id, book):
        self.cursor.execute(
            'INSERT INTO wishlist (user_id, book_title, author_name) VALUES (?, ?, ?)', 
            (user_id, book.title, book.author)
        )
        self.conn.commit()

    def view_wishlist(self, user_id):
        self.cursor.execute('SELECT * FROM wishlist WHERE user_id = ?', (user_id,))
        wishlist_items = self.cursor.fetchall()
        if wishlist_items:
            return [f"Nosaukums: {item[2]}, Autors: {item[3]}" for item in wishlist_items]
        else:
            return ["Jūsu vēlmju saraksts ir tukšs."]

    def remove_book(self, user_id, book_title, author_name):
        self.cursor.execute(
            'DELETE FROM wishlist WHERE user_id = ? AND book_title = ? AND author_name = ?',
            (user_id, book_title, author_name)
        )
        self.conn.commit()
        if self.cursor.rowcount:
            return f"Grāmata '{book_title}' no {author_name} ir noņemta no jūsu vēlmju saraksta."
        else:
            return "Nav atrasta atbilstoša grāmata jūsu vēlmju sarakstā."

    def add_review(self, user_id, book_title, author_name, review):
        self.cursor.execute(
            'INSERT INTO reviews (user_id, book_title, author_name, review) VALUES (?, ?, ?, ?)', 
            (user_id, book_title, author_name, review)
        )
        self.conn.commit()

    def view_reviews(self, book_title, author_name):
        self.cursor.execute('''SELECT u.username, r.review 
                               FROM reviews r 
                               JOIN users u ON r.user_id = u.id 
                               WHERE r.book_title = ? AND r.author_name = ?''', (book_title, author_name))
        reviews = self.cursor.fetchall()
        if reviews:
            return [f"{username}: {review}" for username, review in reviews]
        else:
            return ["Par šo grāmatu vēl nav atsauksmju."]

class Library:
    @staticmethod
    def search_books(query, by="author"):
        if by == "title":
            url = f"http://openlibrary.org/search.json?title={query}"
        else:
            url = f"http://openlibrary.org/search.json?author={query}"
        
        response = requests.get(url)
        if response.status_code == 200:
            books = response.json().get('docs', [])
            books = books[:8]
            return [Book(book.get('title', 'Nav pieejams nosaukums'),
                         book.get('author_name', ['Nezināms'])[0]) for book in books]
        else:
            return []

class BookApp:
    def __init__(self, root, wishlist):
        self.root = root
        self.wishlist = wishlist
        self.user_id = None
        self.current_user = None

        self.root.title("Grāmatu vēlmju saraksts")
        self.root.geometry("600x400")
        self.root.configure(bg='#ffe6f0')
        
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(pady=20)
        
        self.result_frame = tk.Frame(self.root)
        self.result_frame.pack(pady=20)

        self.create_main_widgets()

    def create_main_widgets(self):
        self.title_label = tk.Label(self.main_frame, text="Grāmatu Meistars", font=("Arial", 20))
        self.title_label.grid(row=0, columnspan=2, pady=10)
        
        self.login_button = tk.Button(self.main_frame, text="Ielogoties", width=15, command=self.show_login)
        self.login_button.grid(row=1, column=0, padx=10)
        
        self.register_button = tk.Button(self.main_frame, text="Reģistrēties", width=15, command=self.show_register)
        self.register_button.grid(row=1, column=1, padx=10)

    def show_login(self):
        self.clear_main_frame()
        self.login_label = tk.Label(self.main_frame, text="Lietotājvārds:")
        self.login_label.grid(row=0, column=0)
        self.username_entry = tk.Entry(self.main_frame)
        self.username_entry.grid(row=0, column=1)
        
        self.password_label = tk.Label(self.main_frame, text="Parole:")
        self.password_label.grid(row=1, column=0)
        self.password_entry = tk.Entry(self.main_frame, show="*")
        self.password_entry.grid(row=1, column=1)

        self.login_submit_button = tk.Button(self.main_frame, text="Ielogoties", command=self.login_user)
        self.login_submit_button.grid(row=2, columnspan=2, pady=10)

    def show_register(self):
        self.clear_main_frame()
        self.register_label = tk.Label(self.main_frame, text="Lietotājvārds:")
        self.register_label.grid(row=0, column=0)
        self.register_username_entry = tk.Entry(self.main_frame)
        self.register_username_entry.grid(row=0, column=1)

        self.register_password_label = tk.Label(self.main_frame, text="Parole:")
        self.register_password_label.grid(row=1, column=0)
        self.register_password_entry = tk.Entry(self.main_frame, show="*")
        self.register_password_entry.grid(row=1, column=1)

        self.register_submit_button = tk.Button(self.main_frame, text="Reģistrēties", command=self.register_user)
        self.register_submit_button.grid(row=2, columnspan=2, pady=10)

    def login_user(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if self.wishlist.authenticate_user(username, password):
            self.current_user = username
            self.user_id = self.wishlist.get_user_id(username)
            self.show_user_options()
        else:
            messagebox.showerror("Neizdevās ielogoties", "Nepareizs lietotājvārds vai parole.")

    def register_user(self):

        username = self.register_username_entry.get()
        password = self.register_password_entry.get()
        
        if username and password:
            self.wishlist.add_user(username, password)
            messagebox.showinfo("Reģistrācija veiksmīga", f"Lietotājs {username} ir veiksmīgi reģistrēts.")
            self.show_login()
        else:
            messagebox.showerror("Kļūda", "Lūdzu, aizpildiet visus laukus.")

    def show_user_options(self):
        self.clear_main_frame()
        self.option1 = tk.Button(self.main_frame, text="Pievienot grāmatu vēlmju sarakstam", command=self.add_book)
        self.option1.grid(row=0, column=0, pady=5)

        self.option2 = tk.Button(self.main_frame, text="Apskatīt vēlmju sarakstu", command=self.view_wishlist)
        self.option2.grid(row=1, column=0, pady=5)

        self.option3 = tk.Button(self.main_frame, text="Rakstīt atsauksmi par grāmatu", command=self.add_review)
        self.option3.grid(row=2, column=0, pady=5)

        self.option4 = tk.Button(self.main_frame, text="Lasīt atsauksmes par grāmatu", command=self.view_reviews)
        self.option4.grid(row=3, column=0, pady=5)

        self.option5 = tk.Button(self.main_frame, text="Noņemt grāmatu no vēlmju saraksta", command=self.remove_book)
        self.option5.grid(row=4, column=0, pady=5)

        self.option6 = tk.Button(self.main_frame, text="Iziet", command=self.exit_app)
        self.option6.grid(row=5, column=0, pady=5)

    def add_book(self):
        self.clear_main_frame()
        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:")
        self.book_title_label.grid(row=0, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=0, column=1)

        self.search_button = tk.Button(self.main_frame, text="Meklēt", command=self.search_books)
        self.search_button.grid(row=1, columnspan=2, pady=10)

    def search_books(self):
        query = self.book_title_entry.get()
        if query:
            books = Library.search_books(query, by="title")
            self.display_books(books)

    def display_books(self, books):
        self.clear_main_frame()
        for idx, book in enumerate(books):
            book_button = tk.Button(self.main_frame, text=f"{book.title} - {book.author}",
                                    command=lambda b=book: self.add_book_to_wishlist(b))
            book_button.grid(row=idx, column=0, pady=5)
        
        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options)
        self.back_button.grid(row=len(books), columnspan=2, pady=10)

    def add_book_to_wishlist(self, book):
        if book:
            self.wishlist.add_book(self.user_id, book)
            messagebox.showinfo("Grāmata pievienota", f"Grāmata '{book.title}' ir veiksmīgi pievienota vēlmju sarakstam.")
            self.show_user_options()
        else:
            messagebox.showerror("Kļūda", "Nav izvēlēta grāmata.")

    def view_wishlist(self):
        wishlist_items = self.wishlist.view_wishlist(self.user_id)
        self.clear_main_frame()
        
        for idx, item in enumerate(wishlist_items):
            item_label = tk.Label(self.main_frame, text=item)
            item_label.grid(row=idx, column=0)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options)
        self.back_button.grid(row=len(wishlist_items), columnspan=2, pady=10)

    def add_review(self):
        self.clear_main_frame()
        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:")
        self.book_title_label.grid(row=0, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=0, column=1)

        self.author_name_label = tk.Label(self.main_frame, text="Autora vārds:")
        self.author_name_label.grid(row=1, column=0)
        self.author_name_entry = tk.Entry(self.main_frame)
        self.author_name_entry.grid(row=1, column=1)

        self.review_label = tk.Label(self.main_frame, text="Atsauksme:")
        self.review_label.grid(row=2, column=0)
        self.review_entry = tk.Entry(self.main_frame)
        self.review_entry.grid(row=2, column=1)

        self.submit_review_button = tk.Button(self.main_frame, text="Pievienot atsauksmi", command=self.submit_review)
        self.submit_review_button.grid(row=3, columnspan=2, pady=10)

    def submit_review(self):
        title = self.book_title_entry.get()
        author = self.author_name_entry.get()
        review = self.review_entry.get()

        if title and author and review:
            self.wishlist.add_review(self.user_id, title, author, review)
            messagebox.showinfo("Atsauksme pievienota", "Jūsu atsauksme ir veiksmīgi pievienota.")
            self.show_user_options()
        else:
            messagebox.showerror("Kļūda", "Lūdzu, aizpildiet visus laukus.")

    def view_reviews(self):
        self.clear_main_frame()
        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:")
        self.book_title_label.grid(row=0, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=0, column=1)

        self.author_name_label = tk.Label(self.main_frame, text="Autora vārds:")
        self.author_name_label.grid(row=1, column=0)
        self.author_name_entry = tk.Entry(self.main_frame)
        self.author_name_entry.grid(row=1, column=1)

        self.search_reviews_button = tk.Button(self.main_frame, text="Skatīt atsauksmes", command=self.search_reviews)
        self.search_reviews_button.grid(row=2, columnspan=2, pady=10)

    def search_reviews(self):
        title = self.book_title_entry.get()
        author = self.author_name_entry.get()

        if title and author:
            reviews = self.wishlist.view_reviews(title, author)
            self.display_reviews(reviews)
        else:
            messagebox.showerror("Kļūda", "Lūdzu, aizpildiet visus laukus.")

    def display_reviews(self, reviews):
        self.clear_main_frame()
        for idx, review in enumerate(reviews):
            review_label = tk.Label(self.main_frame, text=review)
            review_label.grid(row=idx, column=0)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options)
        self.back_button.grid(row=len(reviews), columnspan=2, pady=10)

    def remove_book(self):
        self.clear_main_frame()
        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:")
        self.book_title_label.grid(row=0, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=0, column=1)

        self.author_name_label = tk.Label(self.main_frame, text="Autora vārds:")
        self.author_name_label.grid(row=1, column=0)
        self.author_name_entry = tk.Entry(self.main_frame)
        self.author_name_entry.grid(row=1, column=1)

        self.remove_button = tk.Button(self.main_frame, text="Noņemt grāmatu", command=self.remove_selected_book)
        self.remove_button.grid(row=2, columnspan=2, pady=10)

    def remove_selected_book(self):
        title = self.book_title_entry.get()
        author = self.author_name_entry.get()

        if title and author:
            message = self.wishlist.remove_book(self.user_id, title, author)
            messagebox.showinfo("Grāmata noņemta", message)
            self.show_user_options()
        else:
            messagebox.showerror("Kļūda", "Lūdzu, aizpildiet visus laukus.")

    def exit_app(self):
        self.root.quit()

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

def main():
    wishlist = Wishlist()
    root = tk.Tk()
    app = BookApp(root, wishlist)
    root.mainloop()

if __name__ == '__main__':
    main()