try:
    from app import data_handler

    # Test the get_users() method
    print("Testing get_users() method...")
    users = data_handler.get_users()
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
        else:
            print(f"No match - phone match: {user['phone'] == phone}, type match: {user['type'] == user_type}, password match: {user['password'] == password}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
