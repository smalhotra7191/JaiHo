from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import hashlib
import datetime
import json
import pandas as pd
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Google Sheets Configuration
# You'll need to set up Google Sheets API credentials
# scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
# creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
# client = gspread.authorize(creds)

# CSV Data Handler - replaces MockGoogleSheets
class CSVDataHandler:
    def __init__(self, data_folder='data'):
        self.data_folder = data_folder
        self.users_file = os.path.join(data_folder, 'Users.csv')
        self.poojas_file = os.path.join(data_folder, 'Poojas.csv')
        self.bookings_file = os.path.join(data_folder, 'bookings.csv')
        
        # Ensure CSV files exist
        self._ensure_csv_files_exist()
    
    def _ensure_csv_files_exist(self):
        """Create CSV files if they don't exist"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        
        # Check if files exist, if not create them with headers
        if not os.path.exists(self.users_file):
            users_df = pd.DataFrame(columns=['id', 'email', 'password', 'type', 'name', 'phone', 'experience', 'specialization', 'address', 'capacity'])
            users_df.to_csv(self.users_file, index=False)
            
        if not os.path.exists(self.poojas_file):
            poojas_df = pd.DataFrame(columns=['id', 'name', 'name_hi', 'description', 'description_hi', 'duration', 'price'])
            poojas_df.to_csv(self.poojas_file, index=False)
            
        if not os.path.exists(self.bookings_file):
            bookings_df = pd.DataFrame(columns=['id', 'customer_id', 'pooja_id', 'pandit_id', 'mandir_id', 'date', 'status', 'rating', 'review'])
            bookings_df.to_csv(self.bookings_file, index=False)
    
    def get_users(self):
        """Load users from CSV and return as list of dictionaries"""
        try:
            df = pd.read_csv(self.users_file)
            # Replace NaN values with None/empty strings as appropriate
            df = df.fillna('')
            users = []
            for _, row in df.iterrows():
                user = {
                    'id': int(row['id']),
                    'email': row['email'],
                    'password': row['password'],
                    'type': row['type'],
                    'name': row['name'],
                    'phone': str(int(float(row['phone']))),  # Convert to int to remove decimals
                }
                
                # Add optional fields based on user type
                if row['type'] == 'pandit':
                    user['experience'] = int(row['experience']) if row['experience'] and str(row['experience']) != '' else 0
                    user['specialization'] = row['specialization'] if row['specialization'] else ''
                elif row['type'] == 'mandir':
                    user['address'] = row['address'] if row['address'] else ''
                    user['capacity'] = int(row['capacity']) if row['capacity'] and str(row['capacity']) != '' else 0
                
                users.append(user)
            return users
        except Exception as e:
            print(f"Error reading users CSV: {e}")
            return []
    
    def get_poojas(self):
        """Load poojas from CSV and return as list of dictionaries"""
        try:
            df = pd.read_csv(self.poojas_file)
            df = df.fillna('')
            poojas = []
            for _, row in df.iterrows():
                pooja = {
                    'id': int(row['id']),
                    'name': row['name'],
                    'name_hi': row['name_hi'],
                    'description': row['description'],
                    'description_hi': row['description_hi'] if 'description_hi' in row else '',
                    'duration': int(row['duration']),
                    'price': int(row['price'])
                }
                poojas.append(pooja)
            return poojas
        except Exception as e:
            print(f"Error reading poojas CSV: {e}")
            return []
    
    def get_bookings(self):
        """Load bookings from CSV and return as list of dictionaries"""
        try:
            df = pd.read_csv(self.bookings_file)
            df = df.fillna('')
            bookings = []
            for _, row in df.iterrows():
                booking = {
                    'id': int(row['id']),
                    'customer_id': int(row['customer_id']),
                    'pooja_id': int(row['pooja_id']),
                    'pandit_id': int(row['pandit_id']),
                    'mandir_id': int(row['mandir_id']) if row['mandir_id'] and str(row['mandir_id']) != '' else None,
                    'date': row['date'],
                    'status': row['status'],
                    'rating': int(row['rating']) if row['rating'] and str(row['rating']) != '' else None,
                    'review': row['review'] if row['review'] else None
                }
                bookings.append(booking)
            return bookings
        except Exception as e:
            print(f"Error reading bookings CSV: {e}")
            return []
    
    def add_booking(self, booking_data):
        """Add a new booking to the CSV file"""
        try:
            df = pd.read_csv(self.bookings_file)
            
            # Generate new ID
            new_id = df['id'].max() + 1 if not df.empty else 1
            booking_data['id'] = new_id
            
            # Convert to DataFrame row
            new_row = pd.DataFrame([booking_data])
            
            # Append to existing DataFrame
            df = pd.concat([df, new_row], ignore_index=True)
            
            # Save back to CSV
            df.to_csv(self.bookings_file, index=False)
            
            print(f"Added new booking with ID: {new_id}")
            return new_id
        except Exception as e:
            print(f"Error adding booking: {e}")
            return None
    
    def update_booking(self, booking_id, update_data):
        """Update an existing booking in the CSV file"""
        try:
            df = pd.read_csv(self.bookings_file)
            
            # Find the booking to update
            mask = df['id'] == booking_id
            if not mask.any():
                print(f"Booking with ID {booking_id} not found")
                return False
            
            # Update the fields
            for key, value in update_data.items():
                if key in df.columns:
                    df.loc[mask, key] = value
            
            # Save back to CSV
            df.to_csv(self.bookings_file, index=False)
            
            print(f"Updated booking ID: {booking_id}")
            return True
        except Exception as e:
            print(f"Error updating booking: {e}")
            return False

# CSV Data Handler instance - replaces sheets_client
data_handler = CSVDataHandler()

# Multi-language support
translations = {
    'en': {
        'app_title': 'Jai Ho!',
        'sign_in': 'Sign In',
        'customer': 'Customer',
        'pandit': 'Pandit',
        'mandir': 'Mandir',
        'phone': 'Phone Number',
        'password': 'Password',
        'login': 'Login',
        'browse_poojas': 'Browse Poojas',
        'search': 'Search',
        'book_now': 'Book Now',
        'dashboard': 'Dashboard',
        'upcoming_bookings': 'Upcoming Bookings',
        'past_reviews': 'Past Reviews',
        'revenue': 'Revenue',
        'logout': 'Logout',
        'filter_by': 'Filter By',
        'location': 'Location',
        'price_range': 'Price Range',
        'duration': 'Duration',
        'rating': 'Rating',
        'minutes': 'minutes',
        'rupees': '₹',
        'book_pooja': 'Book Pooja',
        'select_date': 'Select Date',
        'select_pandit': 'Select Pandit',
        'select_mandir': 'Select Mandir (Optional)',
        'confirm_booking': 'Confirm Booking',
        'total_bookings': 'Total Bookings',
        'total_revenue': 'Total Revenue',
        'average_rating': 'Average Rating',
        'my_bookings': 'My Bookings',
        'chat': 'Chat',
        'profile': 'Profile',
        'home': 'Home',
        'search_poojas': 'Search Poojas',
        'search_for_poojas': 'Search for poojas...',
        'bookings': 'Bookings',
        'no_bookings': 'No bookings found',
        'upcoming': 'Upcoming',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
        'message_placeholder': 'Type your message...',
        'send': 'Send',
        'edit_profile': 'Edit Profile',
        'name': 'Name',
        'email': 'Email',
        'experience': 'Experience',
        'specialization': 'Specialization',
        'address': 'Address',
        'capacity': 'Capacity',
        'save_changes': 'Save Changes',
        'filter': 'Filter',
        'all_categories': 'All Categories',
        'price_low_to_high': 'Price: Low to High',
        'price_high_to_low': 'Price: High to Low',
        'duration_short': 'Duration: Short',
        'duration_long': 'Duration: Long',
        'apply_filter': 'Apply Filter',
        'clear_filter': 'Clear Filter',
        'daily_worship': 'Daily Worship',
        'view_details': 'View Details',
        'search_results': 'Search Results',
        'found': 'found',
        'clear_search': 'Clear Search',
        'popular_poojas': 'Popular Poojas',
        'no_poojas_found': 'No poojas found',
        'confirmed': 'Confirmed',
        'no_conversations': 'No conversations yet',
        'notifications': 'Notifications',
        'language': 'Language',
        'help_support': 'Help & Support',
        'about': 'About',
        'welcome': 'Welcome',
        'view_profile': 'View Profile',
        'export_report': 'Export Report',
        'booking': 'Booking',
        'date': 'Date',
        'time': 'Time',
        'amount': 'Amount',
        'no_completed_bookings': 'No completed bookings yet',
        'start_booking_message': 'When you complete your first booking, it will appear here.',
        'professional_tip': 'Professional Tip',
        'tip_message': 'Maintain clear communication with customers and always arrive on time to build your reputation.',
        'active_bookings': 'Active Bookings',
        'completed_bookings': 'Completed Bookings',
        'welcome_back': 'Welcome back',
        'from_last_month': 'from last month',
        'based_on_reviews': 'based on',
        'reviews': 'reviews',
        'boost_profile': 'Boost Your Profile',
        'complete_profile_tip': 'Complete your profile to attract more customers and grow your business.',
        'complete_profile': 'Complete Profile',
        'developed_by': 'Developed by Smit Gupta and Sameer Malhotra'
    },
    'hi': {
        'app_title': 'जय हो!',
        'sign_in': 'साइन इन',
        'customer': 'ग्राहक',
        'pandit': 'पंडित',
        'mandir': 'मंदिर',
        'phone': 'फोन नंबर',
        'password': 'पासवर्ड',
        'login': 'लॉगिन',
        'browse_poojas': 'पूजा देखें',
        'search': 'खोजें',
        'book_now': 'अभी बुक करें',
        'dashboard': 'डैशबोर्ड',
        'upcoming_bookings': 'आगामी बुकिंग',
        'past_reviews': 'पिछली समीक्षाएं',
        'revenue': 'आय',
        'logout': 'लॉगआउट',
        'filter_by': 'फ़िल्टर करें',
        'location': 'स्थान',
        'price_range': 'मूल्य सीमा',
        'duration': 'अवधि',
        'rating': 'रेटिंग',
        'minutes': 'मिनट',
        'rupees': '₹',
        'book_pooja': 'पूजा बुक करें',
        'select_date': 'दिनांक चुनें',
        'select_pandit': 'पंडित चुनें',
        'select_mandir': 'मंदिर चुनें (वैकल्पिक)',
        'confirm_booking': 'बुकिंग पुष्टि करें',
        'total_bookings': 'कुल बुकिंग',
        'total_revenue': 'कुल आय',
        'average_rating': 'औसत रेटिंग',
        'my_bookings': 'मेरी बुकिंग',
        'chat': 'चैट',
        'profile': 'प्रोफ़ाइल',
        'home': 'होम',
        'search_poojas': 'पूजा खोजें',
        'search_for_poojas': 'पूजा खोजें...',
        'bookings': 'बुकिंग',
        'no_bookings': 'कोई बुकिंग नहीं मिली',
        'upcoming': 'आगामी',
        'completed': 'पूर्ण',
        'cancelled': 'रद्द',
        'message_placeholder': 'अपना संदेश टाइप करें...',
        'send': 'भेजें',
        'edit_profile': 'प्रोफ़ाइल संपादित करें',
        'name': 'नाम',
        'email': 'ईमेल',
        'experience': 'अनुभव',
        'specialization': 'विशेषज्ञता',
        'address': 'पता',
        'capacity': 'क्षमता',
        'save_changes': 'परिवर्तन सहेजें',
        'filter': 'फ़िल्टर',
        'all_categories': 'सभी श्रेणियां',
        'price_low_to_high': 'मूल्य: कम से अधिक',
        'price_high_to_low': 'मूल्य: अधिक से कम',
        'duration_short': 'अवधि: छोटी',
        'duration_long': 'अवधि: लंबी',
        'apply_filter': 'फ़िल्टर लागू करें',
        'clear_filter': 'फ़िल्टर साफ़ करें',
        'daily_worship': 'दैनिक पूजा',
        'view_details': 'विवरण देखें',
        'search_results': 'खोज परिणाम',
        'found': 'मिले',
        'clear_search': 'खोज साफ़ करें',
        'popular_poojas': 'लोकप्रिय पूजा',
        'no_poojas_found': 'कोई पूजा नहीं मिली',
        'confirmed': 'पुष्टि',
        'no_conversations': 'अभी तक कोई बातचीत नहीं',
        'notifications': 'सूचनाएं',
        'language': 'भाषा',
        'help_support': 'सहायता और समर्थन',
        'about': 'के बारे में',
        'welcome': 'स्वागत',
        'view_profile': 'प्रोफ़ाइल देखें',
        'export_report': 'रिपोर्ट निर्यात करें',
        'booking': 'बुकिंग',
        'date': 'दिनांक',
        'time': 'समय',
        'amount': 'राशि',
        'no_completed_bookings': 'अभी तक कोई पूर्ण बुकिंग नहीं',
        'start_booking_message': 'जब आप अपनी पहली बुकिंग पूरी करेंगे, तो यह यहां दिखाई देगी।',
        'professional_tip': 'व्यावसायिक सुझाव',
        'tip_message': 'ग्राहकों के साथ स्पष्ट संवाद बनाए रखें और अपनी प्रतिष्ठा बनाने के लिए हमेशा समय पर पहुंचें।',
        'active_bookings': 'सक्रिय बुकिंग',
        'completed_bookings': 'पूर्ण बुकिंग',
        'welcome_back': 'वापसी पर स्वागत',
        'from_last_month': 'पिछले महीने से',
        'based_on_reviews': 'आधारित',
        'reviews': 'समीक्षाओं',
        'boost_profile': 'अपनी प्रोफ़ाइल बढ़ाएं',
        'complete_profile_tip': 'अधिक ग्राहकों को आकर्षित करने और अपना व्यवसाय बढ़ाने के लिए अपनी प्रोफ़ाइल पूरी करें।',
        'complete_profile': 'प्रोफ़ाइल पूरी करें',
        'developed_by': 'स्मित गुप्ता और समीर मल्होत्रा द्वारा विकसित',
        'welcome': 'स्वागत',
        'view_profile': 'प्रोफ़ाइल देखें',
        'export_report': 'रिपोर्ट निर्यात करें',
        'booking': 'बुकिंग',
        'date': 'दिनांक',
        'time': 'समय',
        'amount': 'राशि',
        'no_completed_bookings': 'अभी तक कोई पूर्ण बुकिंग नहीं',
        'start_booking_message': 'जब आप अपनी पहली बुकिंग पूरी करेंगे, तो वह यहां दिखाई देगी।',
        'professional_tip': 'व्यावसायिक सुझाव',
        'tip_message': 'अपनी प्रतिष्ठा बनाने के लिए ग्राहकों के साथ स्पष्ट संवाद बनाए रखें और हमेशा समय पर पहुंचें।',
        'active_bookings': 'सक्रिय बुकिंग',
        'completed_bookings': 'पूर्ण बुकिंग'
    }
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('sign_in'))
        
        # Also check if user exists in the data
        user = get_current_user()
        if user is None:
            session.clear()
            return redirect(url_for('sign_in'))
            
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        users = data_handler.get_users()
        for user in users:
            if user['id'] == session['user_id']:
                return user
    return None

def get_translation(key, lang='en'):
    return translations.get(lang, translations['en']).get(key, key)

@app.route('/')
def index():
    if 'user_id' in session:
        user = get_current_user()
        if user and user['type'] == 'customer':
            return redirect(url_for('browse_poojas'))
        elif user:
            return redirect(url_for('dashboard'))
        else:
            # User ID in session but user not found, clear session
            session.clear()
            return redirect(url_for('sign_in'))
    return redirect(url_for('sign_in'))

@app.route('/home')
@login_required
def home():
    return redirect(url_for('browse_poojas'))

@app.route('/sign_in')
def sign_in():
    #lang = request.args.get('lang', 'en')
    lang = session.get('lang', request.args.get('lang', 'en'))
    return render_template('sign_in.html', lang=lang, t=lambda k: get_translation(k, lang))

@app.route('/test_post', methods=['POST'])
def test_post():
    print("Test POST route received!")
    print(f"Form data: {request.form}")
    return "POST request received successfully!"

@app.route('/login', methods=['POST'])
def login():
    print(f"Login attempt received")
    print(f"Form data: {request.form}")
    
    phone = request.form['phone']
    password = request.form['password']
    user_type = request.form['user_type']
    lang = request.form.get('lang', 'en')
    
    print(f"Phone: {phone}, Password: {password}, User Type: {user_type}")
    
    # Simple password hashing for demo (use proper hashing in production)
    # hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    users = data_handler.get_users()
    for user in users:
        if user['phone'] == phone and user['type'] == user_type and user['password'] == password:
            # In production, verify hashed password
            session['user_id'] = user['id']
            session['user_type'] = user['type']
            session['lang'] = lang
            
            print(f"Login successful for user: {user['name']}")
            
            if user_type == 'customer':
                return redirect(url_for('browse_poojas'))
            else:
                return redirect(url_for('dashboard'))
    
    print("Login failed - invalid credentials")
    flash('Invalid credentials', 'error')
    return redirect(url_for('sign_in', lang=lang))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('sign_in'))

@app.route('/browse_poojas')
@login_required
def browse_poojas():
    user = get_current_user()
    if user['type'] != 'customer':
        return redirect(url_for('dashboard'))
    
    lang = session.get('lang', 'en')
    poojas = data_handler.get_poojas()
    pandits = [u for u in data_handler.get_users() if u['type'] == 'pandit']
    mandirs = [u for u in data_handler.get_users() if u['type'] == 'mandir']
    
    # Enhance poojas with additional data for the layout
    enhanced_poojas = []
    for pooja in poojas:
        enhanced_pooja = pooja.copy()
        enhanced_pooja['price_min'] = pooja['price'] - 1000
        enhanced_pooja['price_max'] = pooja['price'] + 1000
        enhanced_pooja['rating'] = 4.8  # Mock rating
        enhanced_pooja['pandits'] = len([p for p in pandits])  # Number of available pandits
        enhanced_pooja['category'] = 'Daily Worship'
        enhanced_pooja['image_url'] = f'/static/images/{pooja["name"].lower().replace(" ", "_")}.jpg'
        enhanced_poojas.append(enhanced_pooja)
    
    # Apply filters if any
    location_filter = request.args.get('location')
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    search_query = request.args.get('q', '')  # Add search query parameter
    
    # Apply search filter
    if search_query:
        filtered_poojas = []
        for pooja in enhanced_poojas:
            if (search_query.lower() in pooja['name'].lower() or 
                search_query.lower() in pooja['description'].lower() or
                search_query.lower() in pooja['name_hi'].lower()):
                filtered_poojas.append(pooja)
        enhanced_poojas = filtered_poojas
    
    # Apply price filters
    if min_price or max_price:
        filtered_poojas = []
        for pooja in enhanced_poojas:
            if min_price and pooja['price'] < min_price:
                continue
            if max_price and pooja['price'] > max_price:
                continue
            filtered_poojas.append(pooja)
        enhanced_poojas = filtered_poojas
    
    # Add profile image URL for the user
    user['profile_image_url'] = '/static/images/default_profile.jpg'  # Default profile image
    
    return render_template('browse_poojas.html', 
                         user=user,
                         poojas=enhanced_poojas,  # Pass enhanced poojas as main poojas list
                         pandits=pandits, 
                         mandirs=mandirs,
                         search_query=search_query,  # Pass search query to template
                         lang=lang, 
                         t=lambda k: get_translation(k, lang))

@app.route('/book_pooja/<int:pooja_id>')
@login_required
def book_pooja(pooja_id):
    user = get_current_user()
    if user['type'] != 'customer':
        return redirect(url_for('dashboard'))
    
    lang = session.get('lang', 'en')
    poojas = data_handler.get_poojas()
    pooja = next((p for p in poojas if p['id'] == pooja_id), None)
    
    if not pooja:
        flash('Pooja not found', 'error')
        return redirect(url_for('browse_poojas'))
    
    pandits = [u for u in data_handler.get_users() if u['type'] == 'pandit']
    mandirs = [u for u in data_handler.get_users() if u['type'] == 'mandir']
    
    return render_template('book_pooja.html', 
                         pooja=pooja, pandits=pandits, mandirs=mandirs,
                         lang=lang, t=lambda k: get_translation(k, lang))

@app.route('/confirm_booking', methods=['POST'])
@login_required
def confirm_booking():
    user = get_current_user()
    if user['type'] != 'customer':
        return redirect(url_for('dashboard'))
    
    booking_data = {
        'customer_id': user['id'],
        'pooja_id': int(request.form['pooja_id']),
        'pandit_id': int(request.form['pandit_id']),
        'mandir_id': int(request.form['mandir_id']) if request.form.get('mandir_id') else None,
        'date': request.form['date'],
        'status': 'confirmed',
        'rating': None,
        'review': None
    }
    
    booking_id = data_handler.add_booking(booking_data)
    flash(f'Booking confirmed! Booking ID: {booking_id}', 'success')
    return redirect(url_for('browse_poojas'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    if user['type'] == 'customer':
        return redirect(url_for('browse_poojas'))
    
    lang = session.get('lang', 'en')
    bookings = data_handler.get_bookings()
    poojas = data_handler.get_poojas()  # Add poojas data
    
    # Filter bookings based on user type
    user_bookings = []
    if user['type'] == 'pandit':
        user_bookings = [b for b in bookings if b['pandit_id'] == user['id']]
    elif user['type'] == 'mandir':
        user_bookings = [b for b in bookings if b['mandir_id'] == user['id']]
    
    # Calculate statistics
    total_bookings = len(user_bookings)
    completed_bookings = [b for b in user_bookings if b['status'] == 'completed']
    total_revenue = sum([p['price'] for p in poojas 
                        for b in completed_bookings if b['pooja_id'] == p['id']])
    
    ratings = [b['rating'] for b in completed_bookings if b['rating']]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    upcoming_bookings = [b for b in user_bookings if b['status'] == 'confirmed']
    past_bookings = [b for b in user_bookings if b['status'] == 'completed']
    
    return render_template('dashboard.html', 
                         user=user,
                         upcoming_bookings=upcoming_bookings,
                         past_bookings=past_bookings,
                         total_bookings=total_bookings,
                         total_revenue=total_revenue,
                         avg_rating=round(avg_rating, 1),
                         poojas=poojas,  # Add poojas to template context
                         lang=lang, t=lambda k: get_translation(k, lang))

@app.route('/search')
@login_required
def search():
    user = get_current_user()
    lang = session.get('lang', 'en')
    
    query = request.args.get('q', '')
    poojas = data_handler.get_poojas()
    
    if query:
        # Filter poojas based on search query
        filtered_poojas = []
        for pooja in poojas:
            if (query.lower() in pooja['name'].lower() or 
                query.lower() in pooja['description'].lower()):
                filtered_poojas.append(pooja)
        poojas = filtered_poojas
    
    return render_template('search.html', 
                         poojas=poojas,
                         query=query,
                         user=user,
                         lang=lang, 
                         t=lambda k: get_translation(k, lang))

@app.route('/bookings')
@login_required
def bookings():
    user = get_current_user()
    lang = session.get('lang', 'en')
    
    # Get user's bookings
    all_bookings = data_handler.get_bookings()
    user_bookings = [b for b in all_bookings if b['customer_id'] == user['id']]
    
    # Enhance bookings with pooja and pandit details
    enhanced_bookings = []
    for booking in user_bookings:
        enhanced_booking = booking.copy()
        
        # Get pooja details
        poojas = data_handler.get_poojas()
        for pooja in poojas:
            if pooja['id'] == booking['pooja_id']:
                enhanced_booking['pooja_name'] = pooja['name']
                enhanced_booking['pooja_price'] = pooja['price']
                break
        
        # Get pandit details
        users = data_handler.get_users()
        for u in users:
            if u['id'] == booking['pandit_id']:
                enhanced_booking['pandit_name'] = u['name']
                break
        
        enhanced_bookings.append(enhanced_booking)
    
    return render_template('bookings.html', 
                         bookings=enhanced_bookings,
                         user=user,
                         lang=lang, 
                         t=lambda k: get_translation(k, lang))

@app.route('/chat')
@login_required
def chat():
    user = get_current_user()
    lang = session.get('lang', 'en')
    
    # Mock chat data - in real app, get from database
    chats = [
        {
            'id': 1,
            'name': 'Pandit Sharma',
            'last_message': 'Pooja confirmed for tomorrow',
            'timestamp': '2 mins ago',
            'unread': True
        },
        {
            'id': 2,
            'name': 'Shri Ram Mandir',
            'last_message': 'Thank you for booking',
            'timestamp': '1 hour ago',
            'unread': False
        }
    ]
    
    return render_template('chat.html', 
                         chats=chats,
                         user=user,
                         lang=lang, 
                         t=lambda k: get_translation(k, lang))

@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    lang = session.get('lang', 'en')
    
    # Add profile image URL
    user['profile_image_url'] = '/static/images/default_profile.jpg'
    
    return render_template('profile.html', 
                         user=user,
                         lang=lang, 
                         t=lambda k: get_translation(k, lang))

@app.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)