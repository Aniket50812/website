import os
import qrcode   # type: ignore
import datetime  
import sqlite3
from datetime import timedelta  
from flask import Flask, render_template, session, redirect, url_for, request # type: ignore


app = Flask(__name__)

# Generate a secret key using os.urandom(24)
app.secret_key = os.urandom(24)

DATABASE = 'users.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_products_db():
    with get_db() as db:
        db.execute(''' 
            CREATE TABLE IF NOT EXISTS products ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT NOT NULL, 
                description TEXT, 
                price REAL NOT NULL 
            ) 
        ''') 
        db.commit()

def init_users_db():
    with get_db() as db:
        db.execute(''' 
            CREATE TABLE IF NOT EXISTS users ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT NOT NULL UNIQUE, 
                password TEXT NOT NULL 
            ) 
        ''') 
        db.commit()

def setup():
    if not os.path.exists(DATABASE):
        init_products_db()  
        init_users_db()     

setup()  
print("Database setup complete")


offers = [
    {"title": "Buy 1 Get 1 Free", "description": "Buy one book and get another one for free!"},
    {"title": "Buy 6 Books, Get 25% Off", "description": "Purchase six books and get a 25% discount on your total order."},
    {"title": "50% Off on Selected Books", "description": "Check out the selected books with 50% off!"}
]


@app.route('/')
def index():
    if 'username' not in session:
        # Redirect to login page if not logged in
        return redirect(url_for('login'))

    # Fetch books from the database
    with get_db() as db:
        books = db.execute('SELECT * FROM books').fetchall()

    # Render index.html with books data
    return render_template('index.html', books=books)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the user exists in the database and handle login logic
        with get_db() as db:
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user and user['password'] == password:  # Add proper password hashing for production
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return "Invalid login credentials, please try again."

    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    
    with get_db() as db:
        try:
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                       (username, password))
            db.commit()
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            return 'Username already exists'



@app.route('/offers')
def offers_page():
    return render_template('offers.html', offers=offers)

@app.route('/cart')
def cart():
    cart_items = session.get('cart', {})
    total_price = sum(item['quantity'] * item['price'] for item in cart_items.values())
    return render_template('cart.html', cart=cart_items, total_price=total_price)

@app.route('/add_to_cart/<int:book_id>', methods=['POST'])
def add_to_cart(book_id):
    # Fetch the book details from the database using the book_id
    with get_db() as db:
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book:
        cart = session.get('cart', {})

        price = float(book['price'])  # No need to remove ₹ symbol if the price is stored as float
        title = book['title']

        if str(book_id) in cart:
            cart[str(book_id)]['quantity'] += 1
        else:
            cart[str(book_id)] = {
                'title': title,
                'price': price,
                'quantity': 1,
            }

        session['cart'] = cart

    return redirect(url_for('cart'))


@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    book_id = request.form['book_id']
    action = request.form['action']
    cart = session.get('cart', {})
    
    if book_id in cart:
        if action == 'increase':
            cart[book_id]['quantity'] += 1
        elif action == 'decrease' and cart[book_id]['quantity'] > 1:
            cart[book_id]['quantity'] -= 1
        
        session['cart'] = cart
    
    return redirect(url_for('cart'))

@app.route('/proceed_to_pay')
def proceed_to_pay():
    cart_items = session.get('cart', {})
    
    if not cart_items:  # Check if cart is empty
        return redirect(url_for('cart'))  # Redirect back to cart if no products are selected

    total_price = sum(item['quantity'] * item['price'] for item in cart_items.values())
    return render_template('proceed_to_pay.html', cart=cart_items, total_price=total_price)


@app.route('/process_payment', methods=['POST'])
def process_payment():
    # Collect user details from the form
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    payment_mode = request.form['payment_mode']
    upi_id = request.form.get('upi_id')

    # Calculate the total price
    cart_items = session.get('cart', {})
    total_price = sum(item['quantity'] * item['price'] for item in cart_items.values())

    # Add delivery charges if payment mode is COD
    delivery_charges = 0
    if payment_mode == 'COD':
        delivery_charges = 100  # Add ₹100 for delivery charges

    total_price += delivery_charges  # Add delivery charges to the total price

    # Generate UPI QR code if the payment mode is UPI
    qr_code_url = None
    if payment_mode == 'UPI' and upi_id:
        upi_url = f"upi://pay?pa={upi_id}&pn={name}&mc=0000&tid=1234567890&url=https://upi.payment/verify"
        qr_code = qrcode.make(upi_url)
        qr_code_path = os.path.join('static', 'qrcode.png')
        qr_code.save(qr_code_path)
        qr_code_url = qr_code_path  # Path to the generated QR code image

    # Calculate expected delivery date (5 days from now)
    expected_delivery_date = datetime.datetime.now() + timedelta(days=5)
    expected_delivery_date = expected_delivery_date.strftime('%Y-%m-%d')

    # Store the order information in session
    session['order_summary'] = {
        'name': name,
        'email': email,
        'phone': phone,
        'address': address,
        'payment_mode': payment_mode,
        'upi_id': upi_id if payment_mode == 'UPI' else None,
        'total_price': total_price,  # Updated with delivery charges if COD
        'delivery_charges': delivery_charges,  # Store delivery charges separately
        'expected_delivery_date': expected_delivery_date
    }

    return redirect(url_for('order_summary'))

@app.route('/order_summary', methods=['POST', 'GET'])
def order_summary():
    order_data = session.get('order_summary', None)  # Get order summary from session

    if not order_data:
        return redirect(url_for('index'))  # If no order found, redirect to homepage

    # Calculate the delivery date (5 days from today)
    delivery_date = (datetime.datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')

    return render_template('order_summary.html', order_summary=order_data, delivery_date=delivery_date)


if __name__ == '__main__':
    app.run(debug=True)