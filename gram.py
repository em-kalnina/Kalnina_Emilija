import mysql.connector
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
    def __init__(self, host, user, password, database):
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password VARBINARY(255) NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS wishlist (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                book_title VARCHAR(255),
                author_name VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                book_title VARCHAR(255),
                author_name VARCHAR(255),
                review TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        self.conn.commit()

    def add_user(self, username, password):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_password))
        self.conn.commit()

    def authenticate_user(self, username, password):
        self.cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
        result = self.cursor.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), bytes(result[0])):
            return True
        return False

    def get_user_id(self, username):
        self.cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_book(self, user_id, book):
        self.cursor.execute('INSERT INTO wishlist (user_id, book_title, author_name) VALUES (%s, %s, %s)',
                            (user_id, book.title, book.author))
        self.conn.commit()

    def view_wishlist(self, user_id):
        self.cursor.execute('SELECT book_title, author_name FROM wishlist WHERE user_id = %s', (user_id,))
        wishlist_items = self.cursor.fetchall()
        return [f"Nosaukums: {title}, Autors: {author}" for title, author in wishlist_items] if wishlist_items else ["Jūsu vēlmju saraksts ir tukšs."]

    def remove_book(self, user_id, book_title, author_name):
        self.cursor.execute('DELETE FROM wishlist WHERE user_id = %s AND book_title = %s AND author_name = %s',
                            (user_id, book_title, author_name))
        self.conn.commit()
        if self.cursor.rowcount:
            return f"Grāmata '{book_title}' no {author_name} ir noņemta no jūsu vēlmju saraksta."
        else:
            return "Nav atrasta atbilstoša grāmata jūsu vēlmju sarakstā."

    def add_review(self, user_id, book_title, author_name, review):
        self.cursor.execute('INSERT INTO reviews (user_id, book_title, author_name, review) VALUES (%s, %s, %s, %s)',
                            (user_id, book_title, author_name, review))
        self.conn.commit()

    def view_reviews(self, book_title, author_name):
        self.cursor.execute('''
            SELECT u.username, r.review FROM reviews r 
            JOIN users u ON r.user_id = u.id 
            WHERE r.book_title = %s AND r.author_name = %s
        ''', (book_title, author_name))
        reviews = self.cursor.fetchall()
        return [f"{username}: {review}" for username, review in reviews] if reviews else ["Par šo grāmatu vēl nav atsauksmju."]

class Library:
    @staticmethod
    def search_books(query, by="author"):
        url = f"http://openlibrary.org/search.json?{by}={query}"
        response = requests.get(url)
        if response.status_code == 200:
            books = response.json().get('docs', [])[:8]
            return [Book(book.get('title', 'Nav pieejams nosaukums'),
                         book.get('author_name', ['Nezināms'])[0]) for book in books]
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
        
        self.main_frame = tk.Frame(self.root, bg='#ffe6f0')
        self.main_frame.pack(pady=20)
        
        self.result_frame = tk.Frame(self.root, bg='#ffe6f0')
        self.result_frame.pack(pady=20)

        self.create_main_widgets()

    def create_main_widgets(self):
        self.title_label = tk.Label(self.main_frame, text="Grāmatu Meistars", font=("Arial", 20), bg='#ffe6f0')
        self.title_label.grid(row=0, columnspan=2, pady=10)
        
        self.login_button = tk.Button(self.main_frame, text="Ielogoties", width=15, command=self.show_login, bg='#ff8fa6', relief='solid')
        self.login_button.grid(row=1, column=0, padx=10)
        
        self.register_button = tk.Button(self.main_frame, text="Reģistrēties", width=15, command=self.show_register, bg='#ff8fa6', relief='solid')
        self.register_button.grid(row=1, column=1, padx=10)

    def show_login(self):
        self.clear_main_frame()
        self.login_label = tk.Label(self.main_frame, text="Lietotājvārds:", bg='#ffe6f0')
        self.login_label.grid(row=0, column=0)
        self.username_entry = tk.Entry(self.main_frame)
        self.username_entry.grid(row=0, column=1)
        
        self.password_label = tk.Label(self.main_frame, text="Parole:", bg='#ffe6f0')
        self.password_label.grid(row=1, column=0)
        self.password_entry = tk.Entry(self.main_frame, show="*")
        self.password_entry.grid(row=1, column=1)

        self.login_submit_button = tk.Button(self.main_frame, text="Ielogoties", command=self.login_user, bg='#ff8fa6', relief='solid')
        self.login_submit_button.grid(row=2, columnspan=2, pady=10)

    def show_register(self):
        self.clear_main_frame()
        self.register_label = tk.Label(self.main_frame, text="Lietotājvārds:", bg='#ffe6f0')
        self.register_label.grid(row=0, column=0)
        self.register_username_entry = tk.Entry(self.main_frame)
        self.register_username_entry.grid(row=0, column=1)

        self.register_password_label = tk.Label(self.main_frame, text="Parole:", bg='#ffe6f0')
        self.register_password_label.grid(row=1, column=0)
        self.register_password_entry = tk.Entry(self.main_frame, show="*")
        self.register_password_entry.grid(row=1, column=1)

        self.register_submit_button = tk.Button(self.main_frame, text="Reģistrēties", command=self.register_user, bg='#ff8fa6', relief='solid')
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
        self.option1 = tk.Button(self.main_frame, text="Pievienot grāmatu vēlmju sarakstam", command=self.add_book, bg='#ff8fa6', relief='solid')
        self.option1.grid(row=0, column=0, pady=5)

        self.option2 = tk.Button(self.main_frame, text="Apskatīt vēlmju sarakstu", command=self.view_wishlist, bg='#ff8fa6', relief='solid')
        self.option2.grid(row=1, column=0, pady=5)

        self.option3 = tk.Button(self.main_frame, text="Rakstīt atsauksmi par grāmatu", command=self.add_review, bg='#ff8fa6', relief='solid')
        self.option3.grid(row=2, column=0, pady=5)

        self.option4 = tk.Button(self.main_frame, text="Lasīt atsauksmes par grāmatu", command=self.view_reviews, bg='#ff8fa6', relief='solid')
        self.option4.grid(row=3, column=0, pady=5)

        self.option5 = tk.Button(self.main_frame, text="Noņemt grāmatu no vēlmju saraksta", command=self.remove_book, bg='#ff8fa6', relief='solid')
        self.option5.grid(row=4, column=0, pady=5)

        self.option6 = tk.Button(self.main_frame, text="Iziet", command=self.exit_app, bg='#ff8fa6', relief='solid')
        self.option6.grid(row=5, column=0, pady=5)

    def add_book(self):
        self.clear_main_frame()
        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:", bg='#ffe6f0')
        self.book_title_label.grid(row=0, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=0, column=1)

        self.search_button = tk.Button(self.main_frame, text="Meklēt", command=self.search_books, bg='#ff8fa6', relief='solid')
        self.search_button.grid(row=1, columnspan=2, pady=10)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=3, columnspan=2, pady=10)

    def search_books(self):
        query = self.book_title_entry.get()
        if query:
            books = Library.search_books(query, by="title")
            self.display_books(books)

    def display_books(self, books):
        self.clear_main_frame()
        for idx, book in enumerate(books):
            book_button = tk.Button(self.main_frame, text=f"{book.title} - {book.author}",
                                    command=lambda b=book: self.add_book_to_wishlist(b), bg='#ff8fa6', relief='solid')
            book_button.grid(row=idx, column=0, pady=5)
        
        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
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
            item_label = tk.Label(self.main_frame, text=item, bg='#ffe6f0')
            item_label.grid(row=idx, column=0)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=len(wishlist_items), columnspan=2, pady=10)

    def add_review(self):
        self.clear_main_frame()
        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:", bg='#ffe6f0')
        self.book_title_label.grid(row=0, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=0, column=1)

        self.author_name_label = tk.Label(self.main_frame, text="Autora vārds:", bg='#ffe6f0')
        self.author_name_label.grid(row=1, column=0)
        self.author_name_entry = tk.Entry(self.main_frame)
        self.author_name_entry.grid(row=1, column=1)

        self.review_label = tk.Label(self.main_frame, text="Atsauksme:", bg='#ffe6f0')
        self.review_label.grid(row=2, column=0)
        self.review_entry = tk.Entry(self.main_frame)
        self.review_entry.grid(row=2, column=1)

        self.submit_review_button = tk.Button(self.main_frame, text="Pievienot atsauksmi", command=self.submit_review, bg='#ff8fa6', relief='solid')
        self.submit_review_button.grid(row=3, columnspan=2, pady=10)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=4, columnspan=2, pady=10)

    def submit_review(self):
        book_title = self.book_title_entry.get()
        author_name = self.author_name_entry.get()
        review = self.review_entry.get()
        
        if book_title and author_name and review:
            self.wishlist.add_review(self.user_id, book_title, author_name, review)
            messagebox.showinfo("Atsauksme pievienota", "Jūsu atsauksme ir veiksmīgi pievienota!")
            self.show_user_options()
        else:
            messagebox.showerror("Kļūda", "Lūdzu aizpildiet visus laukus.")

    def view_reviews(self):
        self.clear_main_frame()
        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:", bg='#ffe6f0')
        self.book_title_label.grid(row=0, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=0, column=1)

        self.author_name_label = tk.Label(self.main_frame, text="Autora vārds:", bg='#ffe6f0')
        self.author_name_label.grid(row=1, column=0)
        self.author_name_entry = tk.Entry(self.main_frame)
        self.author_name_entry.grid(row=1, column=1)

        self.submit_review_button = tk.Button(self.main_frame, text="Skatīt atsauksmes", command=self.submit_view_reviews, bg='#ff8fa6', relief='solid')
        self.submit_review_button.grid(row=2, columnspan=2, pady=10)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=3, columnspan=2, pady=10)

    def submit_view_reviews(self):
        book_title = self.book_title_entry.get()
        author_name = self.author_name_entry.get()

        if book_title and author_name:
            reviews = self.wishlist.view_reviews(book_title, author_name)
            self.clear_main_frame()
            for idx, review in enumerate(reviews):
                review_label = tk.Label(self.main_frame, text=review, bg='#ffe6f0')
                review_label.grid(row=idx, column=0)

            self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
            self.back_button.grid(row=len(reviews), columnspan=2, pady=10)

    def remove_book(self):
        self.clear_main_frame()
        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:", bg='#ffe6f0')
        self.book_title_label.grid(row=0, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=0, column=1)

        self.author_name_label = tk.Label(self.main_frame, text="Autora vārds:", bg='#ffe6f0')
        self.author_name_label.grid(row=1, column=0)
        self.author_name_entry = tk.Entry(self.main_frame)
        self.author_name_entry.grid(row=1, column=1)

        self.submit_remove_button = tk.Button(self.main_frame, text="Noņemt grāmatu", command=self.submit_remove_book, bg='#ff8fa6', relief='solid')
        self.submit_remove_button.grid(row=2, columnspan=2, pady=10)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=3, columnspan=2, pady=10)

    def submit_remove_book(self):
        book_title = self.book_title_entry.get()
        author_name = self.author_name_entry.get()

        if book_title and author_name:
            message = self.wishlist.remove_book(self.user_id, book_title, author_name)
            messagebox.showinfo("Rezultāts", message)
            self.show_user_options()
        else:
            messagebox.showerror("Kļūda", "Lūdzu, aizpildiet visus laukus.")

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.grid_forget()

    def exit_app(self):
        self.root.quit()

def main():
    db_config = {
        "host": "db4free.net",           
        "user": "emilijak",
        "password": "hyvDuc-supko5-mirxag",
        "database": "bookwishlist"
    }

    wishlist = Wishlist(**db_config)
    root = tk.Tk()
    app = BookApp(root, wishlist)
    root.mainloop()

if __name__ == "__main__":
    main()