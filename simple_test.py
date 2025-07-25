import pandas as pd
import os

# Test CSV reading directly
data_folder = 'data'
users_file = os.path.join(data_folder, 'Users.csv')

try:
    df = pd.read_csv(users_file)
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
        users.append(user)
        
    print(f"Found {len(users)} users:")
    for user in users:
        print(f"ID: {user['id']}, Phone: '{user['phone']}', Type: {user['type']}, Name: {user['name']}")
        print(f"Password: '{user['password']}'")
        print("-" * 50)
        
    # Test login logic
    print("\nTesting login logic:")
    phone = "9876543210"
    password = "hashed_pass"
    user_type = "customer"
    
    for user in users:
        print(f"Checking user: phone='{user['phone']}', type='{user['type']}', password='{user['password']}'")
        if user['phone'] == phone and user['type'] == user_type and user['password'] == password:
            print("MATCH FOUND!")
            break
    else:
        print("NO MATCH FOUND!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
