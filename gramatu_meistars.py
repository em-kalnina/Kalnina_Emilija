import mysql.connector
import bcrypt
import requests
import tkinter as tk
from tkinter import messagebox
from mysql.connector import Error, IntegrityError

# Grāmatas klase, satur grāmatas nosaukumu un autoru
class Book:
    def __init__(self, title, author):
        self.title = title
        self.author = author

    def __str__(self):
        return f"Nosaukums: {self.title}, Autors: {self.author}"

# Datubāzes klase, kas nodrošina savienojumu ar MySQL datubāzi
class Database:
    def __init__(self, host, user, password, database):
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        self.cursor = self.conn.cursor()

# Vēlmju saraksta klase, kas manto datubāzes klasi
    def __init__(self, host, user, password, database):
        super().__init__(host, user, password, database)
        self.create_tables()

    # Izveido nepieciešamās tabulas datubāzē
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

    # Pievieno jaunu lietotāju datubāzē ar šifrētu paroli
    def add_user(self, username, password):
        try:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            self.cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_password))
            self.conn.commit()
            return True
        except IntegrityError:
            # Lietotājvārds jau eksistē
            return False
        except Error as e:
            print(f"Datu bāzes kļūda pievienojot lietotāju: {e}")
            return False

    # Autentificē lietotāju, pārbaudot ievadīto paroli
    def authenticate_user(self, username, password):
        self.cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
        result = self.cursor.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), bytes(result[0])):
            return True
        return False

    #Atrod lietotāja ID pēc lietotājvārda
    def get_user_id(self, username):
        self.cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    #Pievieno grāmatu lietotāja vēlmju sarakstā
    def add_book(self, user_id, book):
        try:
            self.cursor.execute('INSERT INTO wishlist (user_id, book_title, author_name) VALUES (%s, %s, %s)',
                                (user_id, book.title, book.author))
            self.conn.commit()
            return True
        except Error as e:
            print(f"Kļūda pievienojot grāmatu: {e}")
            return False

    #Iegūst visas grāmatas no lietotāja vēlmju saraksta
    def view_wishlist(self, user_id):
        self.cursor.execute('SELECT book_title, author_name FROM wishlist WHERE user_id = %s', (user_id,))
        wishlist_items = self.cursor.fetchall()
        return [f"Nosaukums: {title}, Autors: {author}" for title, author in wishlist_items] if wishlist_items else ["Jūsu vēlmju saraksts ir tukšs."]

    #Noņem grāmatu no lietotāja vēlmju saraksta
    def remove_book(self, user_id, book_title, author_name):
        self.cursor.execute('DELETE FROM wishlist WHERE user_id = %s AND book_title = %s AND author_name = %s',
                            (user_id, book_title, author_name))
        self.conn.commit()
        if self.cursor.rowcount:
            return f"Grāmata '{book_title}' no {author_name} ir noņemta no jūsu vēlmju saraksta."
        else:
            return "Nav atrasta atbilstoša grāmata jūsu vēlmju sarakstā."

    #Pievieno lietotāja atsauksmi par grāmatu
    def add_review(self, user_id, book_title, author_name, review):
        self.cursor.execute('INSERT INTO reviews (user_id, book_title, author_name, review) VALUES (%s, %s, %s, %s)',
                            (user_id, book_title, author_name, review))
        self.conn.commit()

    #Iegūst visas atsauksmes par konkrētu grāmatu
    def view_reviews(self, book_title, author_name):
        self.cursor.execute('''
            SELECT u.username, r.review FROM reviews r 
            JOIN users u ON r.user_id = u.id 
            WHERE r.book_title = %s AND r.author_name = %s
        ''', (book_title, author_name))
        reviews = self.cursor.fetchall()
        return [f"{username}: {review}" for username, review in reviews] if reviews else ["Par šo grāmatu vēl nav atsauksmju."]

#Bibliotēkas klase, kas nodrošina grāmatu meklēšanu no OpenLibrary API
class Library:
    @staticmethod
    def search_books(query, by="title"):
        url = f"http://openlibrary.org/search.json?{by}={query}"
        response = requests.get(url)
        if response.status_code == 200:
            books = response.json().get('docs', [])[:8]
            return [Book(book.get('title', 'Nav pieejams nosaukums'),
                         book.get('author_name', ['Nezināms'])[0]) for book in books]
        return []

# Galvenā lietotāja interfeisa klase, kas izmanto tkinter
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

        self.create_main_widgets()

    #Izveido sākuma izvēlni ar pogām "Ielogoties" un "Reģistrēties"
    def create_main_widgets(self):
        self.clear_main_frame()
        self.title_label = tk.Label(self.main_frame, text="Grāmatu Meistars", font=("Arial", 20), bg='#ffe6f0')
        self.title_label.grid(row=0, columnspan=2, pady=10)

        self.login_button = tk.Button(self.main_frame, text="Ielogoties", width=15, command=self.show_login, bg='#ff8fa6', relief='solid')
        self.login_button.grid(row=1, column=0, padx=10)

        self.register_button = tk.Button(self.main_frame, text="Reģistrēties", width=15, command=self.show_register, bg='#ff8fa6', relief='solid')
        self.register_button.grid(row=1, column=1, padx=10)

    #Rāda pieteikšanās logu
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

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.create_main_widgets, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=3, columnspan=2, pady=5)

    #Rāda reģistrācijas logu
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

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.create_main_widgets, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=3, columnspan=2, pady=5)

    #Apstrādā pieteikšanos
    def login_user(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if self.wishlist.authenticate_user(username, password):
            self.current_user = username
            self.user_id = self.wishlist.get_user_id(username)
            self.show_user_options()
        else:
            messagebox.showerror("Neizdevās ielogoties", "Nepareizs lietotājvārds vai parole.")

    #Apstrādā reģistrāciju
    def register_user(self):
        username = self.register_username_entry.get()
        password = self.register_password_entry.get()

        if username and password:
            success = self.wishlist.add_user(username, password)
            if success:
                messagebox.showinfo("Reģistrācija veiksmīga", f"Lietotājs {username} ir veiksmīgi reģistrēts.")
                self.show_login()
            else:
                messagebox.showerror("Kļūda", "Lietotājvārds jau ir aizņemts vai radās cita problēma.")
        else:
            messagebox.showerror("Kļūda", "Lūdzu, aizpildiet visus laukus.")

    #Rāda galveno izvēlni pēc pieteikšanās
    def show_user_options(self):
        self.clear_main_frame()
        self.option1 = tk.Button(self.main_frame, text="Pievienot grāmatu vēlmju sarakstam", command=self.add_book, bg='#ff8fa6', relief='solid')
        self.option1.grid(row=0, column=0, pady=5)

        self.option2 = tk.Button(self.main_frame, text="Apskatīt vēlmju sarakstu", command=self.view_wishlist, bg='#ff8fa6', relief='solid')
        self.option2.grid(row=1, column=0, pady=5)

        self.option3 = tk.Button(self.main_frame, text="Rakstīt atsauksmi par grāmatu", command=self.add_review, bg='#ff8fa6', relief='solid')
        self.option3.grid(row=2, column=0, pady=5)

        self.option4 = tk.Button(self.main_frame, text="Apskatīt atsauksmes par grāmatu", command=self.view_reviews, bg='#ff8fa6', relief='solid')
        self.option4.grid(row=3, column=0, pady=5)

        self.logout_button = tk.Button(self.main_frame, text="Iziet", command=self.logout_user, bg='#ff8fa6', relief='solid')
        self.logout_button.grid(row=4, column=0, pady=10)

    #Rāda grāmatu meklēšanas un pievienošanas logu
    def add_book(self):
        self.clear_main_frame()

        self.search_label = tk.Label(self.main_frame, text="Meklēt grāmatu (nosaukums vai autors):", bg='#ffe6f0')
        self.search_label.grid(row=0, column=0, columnspan=2, pady=5)

        self.search_entry = tk.Entry(self.main_frame, width=40)
        self.search_entry.grid(row=1, column=0, pady=5)

        self.search_by_var = tk.StringVar(value="title")
        self.radio_title = tk.Radiobutton(self.main_frame, text="Nosaukums", variable=self.search_by_var, value="title", bg='#ffe6f0')
        self.radio_title.grid(row=1, column=1, sticky='w')
        self.radio_author = tk.Radiobutton(self.main_frame, text="Autors", variable=self.search_by_var, value="author", bg='#ffe6f0')
        self.radio_author.grid(row=2, column=1, sticky='w')

        self.search_button = tk.Button(self.main_frame, text="Meklēt", command=self.search_books, bg='#ff8fa6', relief='solid')
        self.search_button.grid(row=3, column=0, pady=10)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=3, column=1, pady=10)

        self.books_listbox = tk.Listbox(self.main_frame, width=70, height=10)
        self.books_listbox.grid(row=4, column=0, columnspan=2, pady=5)

        self.add_selected_button = tk.Button(self.main_frame, text="Pievienot izvēlēto grāmatu vēlmju sarakstam", command=self.add_selected_book, bg='#ff8fa6', relief='solid')
        self.add_selected_button.grid(row=5, column=0, columnspan=2, pady=10)

        self.search_results = []

    #Meklē grāmatas OpenLibrary API un attēlo rezultātus sarakstā
    def search_books(self):
        query = self.search_entry.get().strip()
        by = self.search_by_var.get()

        if not query:
            messagebox.showwarning("Brīdinājums", "Lūdzu, ievadiet meklējamo tekstu.")
            return

        self.books_listbox.delete(0, tk.END)
        self.search_results = Library.search_books(query, by)

        if self.search_results:
            for book in self.search_results:
                self.books_listbox.insert(tk.END, f"{book.title} — {book.author}")
        else:
            self.books_listbox.insert(tk.END, "Nav atrastas grāmatas.")

    #Pievieno izvēlēto grāmatu lietotāja vēlmju sarakstā
    def add_selected_book(self):
        try:
            selected_index = self.books_listbox.curselection()
            if not selected_index:
                messagebox.showwarning("Brīdinājums", "Lūdzu, izvēlieties grāmatu sarakstā.")
                return

            selected_book = self.search_results[selected_index[0]]
            success = self.wishlist.add_book(self.user_id, selected_book)

            if success:
                messagebox.showinfo("Veiksmīgi", f"Grāmata '{selected_book.title}' ir pievienota jūsu vēlmju sarakstam.")
            else:
                messagebox.showerror("Kļūda", "Grāmatu nevarēja pievienot. Iespējams, tā jau ir sarakstā.")
        except Exception as e:
            messagebox.showerror("Kļūda", f"Radās problēma: {e}")

    #Rāda lietotāja vēlmju sarakstu
    def view_wishlist(self):
        self.clear_main_frame()
        wishlist_items = self.wishlist.view_wishlist(self.user_id)

        self.wishlist_label = tk.Label(self.main_frame, text="Jūsu vēlmju saraksts:", font=("Arial", 14), bg='#ffe6f0')
        self.wishlist_label.pack(pady=10)

        self.wishlist_listbox = tk.Listbox(self.main_frame, width=70, height=10)
        self.wishlist_listbox.pack(pady=5)
        for item in wishlist_items:
            self.wishlist_listbox.insert(tk.END, item)

        self.remove_button = tk.Button(self.main_frame, text="Noņemt izvēlēto grāmatu", command=self.remove_selected_book, bg='#ff8fa6', relief='solid')
        self.remove_button.pack(pady=10)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
        self.back_button.pack()

    #Noņem izvēlēto grāmatu no lietotāja vēlmju saraksta
    def remove_selected_book(self):
        try:
            selected_index = self.wishlist_listbox.curselection()
            if not selected_index:
                messagebox.showwarning("Brīdinājums", "Lūdzu, izvēlieties grāmatu sarakstā.")
                return

            selected_text = self.wishlist_listbox.get(selected_index)
            if selected_text.startswith("Nosaukums: ") and ", Autors: " in selected_text:
                title = selected_text.split(", Autors: ")[0].replace("Nosaukums: ", "").strip()
                author = selected_text.split(", Autors: ")[1].strip()
            else:
                messagebox.showerror("Kļūda", "Nekoreks formāts grāmatu sarakstā.")
                return

            message = self.wishlist.remove_book(self.user_id, title, author)
            messagebox.showinfo("Informācija", message)
            self.view_wishlist()
        except Exception as e:
            messagebox.showerror("Kļūda", f"Radās problēma: {e}")

    #Rāda atsauksmju pievienošanas logu
    def add_review(self):
        self.clear_main_frame()
        self.review_label = tk.Label(self.main_frame, text="Atsauksme par grāmatu", font=("Arial", 14), bg='#ffe6f0')
        self.review_label.grid(row=0, column=0, columnspan=2, pady=10)

        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:", bg='#ffe6f0')
        self.book_title_label.grid(row=1, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=1, column=1)

        self.author_label = tk.Label(self.main_frame, text="Autora vārds:", bg='#ffe6f0')
        self.author_label.grid(row=2, column=0)
        self.author_entry = tk.Entry(self.main_frame)
        self.author_entry.grid(row=2, column=1)

        self.review_text_label = tk.Label(self.main_frame, text="Jūsu atsauksme:", bg='#ffe6f0')
        self.review_text_label.grid(row=3, column=0)
        self.review_text = tk.Text(self.main_frame, width=40, height=5)
        self.review_text.grid(row=3, column=1)

        self.submit_review_button = tk.Button(self.main_frame, text="Pievienot atsauksmi", command=self.submit_review, bg='#ff8fa6', relief='solid')
        self.submit_review_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=5, column=0, columnspan=2)

    #Pievieno atsauksmi datubāzē
    def submit_review(self):
        book_title = self.book_title_entry.get().strip()
        author_name = self.author_entry.get().strip()
        review = self.review_text.get("1.0", tk.END).strip()

        if not book_title or not author_name or not review:
            messagebox.showwarning("Brīdinājums", "Lūdzu, aizpildiet visus laukus.")
            return

        self.wishlist.add_review(self.user_id, book_title, author_name, review)
        messagebox.showinfo("Veiksmīgi", "Atsauksme ir pievienota.")
        self.show_user_options()

    #Rāda atsauksmju skatīšanas logu
    def view_reviews(self):
        self.clear_main_frame()
        self.view_review_label = tk.Label(self.main_frame, text="Skatīt atsauksmes par grāmatu", font=("Arial", 14), bg='#ffe6f0')
        self.view_review_label.grid(row=0, column=0, columnspan=2, pady=10)

        self.book_title_label = tk.Label(self.main_frame, text="Grāmatas nosaukums:", bg='#ffe6f0')
        self.book_title_label.grid(row=1, column=0)
        self.book_title_entry = tk.Entry(self.main_frame)
        self.book_title_entry.grid(row=1, column=1)

        self.author_label = tk.Label(self.main_frame, text="Autora vārds:", bg='#ffe6f0')
        self.author_label.grid(row=2, column=0)
        self.author_entry = tk.Entry(self.main_frame)
        self.author_entry.grid(row=2, column=1)

        self.search_reviews_button = tk.Button(self.main_frame, text="Skatīt atsauksmes", command=self.display_reviews, bg='#ff8fa6', relief='solid')
        self.search_reviews_button.grid(row=3, column=0, columnspan=2, pady=10)

        self.reviews_listbox = tk.Listbox(self.main_frame, width=70, height=10)
        self.reviews_listbox.grid(row=4, column=0, columnspan=2)

        self.back_button = tk.Button(self.main_frame, text="Atpakaļ", command=self.show_user_options, bg='#ff8fa6', relief='solid')
        self.back_button.grid(row=5, column=0, columnspan=2, pady=5)

    #Iegūst un attēlo atsauksmes par grāmatu
    def display_reviews(self):
        book_title = self.book_title_entry.get().strip()
        author_name = self.author_entry.get().strip()

        if not book_title or not author_name:
            messagebox.showwarning("Brīdinājums", "Lūdzu, aizpildiet grāmatas nosaukumu un autora vārdu.")
            return

        self.reviews_listbox.delete(0, tk.END)
        reviews = self.wishlist.view_reviews(book_title, author_name)

        for review in reviews:
            self.reviews_listbox.insert(tk.END, review)

    #Iziet no lietotāja konta un atgriežas sākuma izvēlnē
    def logout_user(self):
        self.user_id = None
        self.current_user = None
        self.create_main_widgets()

    #Notīra galveno logu no visiem esošajiem elementiem
    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    #Iziet no lietotnes
    def exit_app(self):
        self.root.quit()

# Galvenā funkcija, kas inicializē datubāzi un palaiž lietotni
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
