import sqlite3

def create_database():
    """Create the database and USERS table"""
    conn = sqlite3.connect('loginusers.db')
    cursor = conn.cursor()
    
    # Create USERS table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS USERS (
            full_name TEXT PRIMARY KEY,
            user_name TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database 'loginusers.db' created successfully with USERS table.")

def add_user():
    """Add a new user to the database"""
    # Get user information from user
    full_name = input("Enter user's full name: ")
    user_name = input("Enter username: ")
    password = input("Enter password: ")
    role = input("Enter role (e.g., admin, teacher, student, parent): ")
    
    try:
        # Insert into database
        conn = sqlite3.connect('loginusers.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO USERS (full_name, user_name, password, role)
            VALUES (?, ?, ?, ?)
        ''', (full_name, user_name, password, role))
        
        conn.commit()
        conn.close()
        
        print(f"User '{full_name}' with username '{user_name}' added successfully.")
        
    except sqlite3.IntegrityError as e:
        if "full_name" in str(e):
            print(f"Error: A user with the name '{full_name}' already exists in the database.")
        elif "user_name" in str(e):
            print(f"Error: Username '{user_name}' is already taken. Please choose a different username.")
        else:
            print(f"Error: {e}")
    except Exception as e:
        print(f"Error adding user: {e}")

def view_users():
    """View all users in the database"""
    conn = sqlite3.connect('loginusers.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT full_name, user_name, password, role FROM USERS')
    users = cursor.fetchall()
    
    if users:
        print("\nUsers in database:")
        print("-" * 85)
        print(f"{'Full Name':<25} {'Username':<20} {'Password':<20} {'Role':<15}")
        print("-" * 85)
        for user in users:
            print(f"{user[0]:<25} {user[1]:<20} {user[2]:<20} {user[3]:<15}")
    else:
        print("No users found in the database.")
    
    conn.close()

def delete_user():
    """Delete a user from the database"""
    identifier = input("Enter the full name or username of the user to delete: ")
    
    try:
        conn = sqlite3.connect('loginusers.db')
        cursor = conn.cursor()
        
        # Check if user exists by full name or username
        cursor.execute('SELECT full_name FROM USERS WHERE full_name = ? OR user_name = ?', (identifier, identifier))
        user = cursor.fetchone()
        
        if user is None:
            print(f"No user found with the name or username '{identifier}'.")
            conn.close()
            return
        
        # Delete the user
        cursor.execute('DELETE FROM USERS WHERE full_name = ? OR user_name = ?', (identifier, identifier))
        conn.commit()
        conn.close()
        
        print(f"User '{identifier}' deleted successfully.")
        
    except Exception as e:
        print(f"Error deleting user: {e}")

def update_user():
    """Update user information"""
    identifier = input("Enter the full name or username of the user to update: ")
    
    try:
        conn = sqlite3.connect('loginusers.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT * FROM USERS WHERE full_name = ? OR user_name = ?', (identifier, identifier))
        user = cursor.fetchone()
        
        if user is None:
            print(f"No user found with the name or username '{identifier}'.")
            conn.close()
            return
        
        print(f"\nCurrent information for '{user[0]}':")
        print(f"Username: {user[1]}")
        print(f"Password: {user[2]}")
        print(f"Role: {user[3]}")
        
        print("\nEnter new information (press Enter to keep current value):")
        new_user_name = input(f"Username ({user[1]}): ") or user[1]
        new_password = input(f"Password ({user[2]}): ") or user[2]
        new_role = input(f"Role ({user[3]}): ") or user[3]
        
        # Update the user
        cursor.execute('''
            UPDATE USERS 
            SET user_name = ?, password = ?, role = ?
            WHERE full_name = ?
        ''', (new_user_name, new_password, new_role, user[0]))
        
        conn.commit()
        conn.close()
        
        print(f"User '{user[0]}' updated successfully.")
        
    except sqlite3.IntegrityError:
        print(f"Error: Username '{new_user_name}' is already taken. Please choose a different username.")
    except Exception as e:
        print(f"Error updating user: {e}")

def search_user():
    """Search for a user by name, username, or role"""
    search_term = input("Enter full name, username, or role to search: ")
    
    conn = sqlite3.connect('loginusers.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT full_name, user_name, password, role 
        FROM USERS 
        WHERE full_name LIKE ? OR user_name LIKE ? OR role LIKE ?
    ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
    
    users = cursor.fetchall()
    
    if users:
        print(f"\nSearch results for '{search_term}':")
        print("-" * 85)
        print(f"{'Full Name':<25} {'Username':<20} {'Password':<20} {'Role':<15}")
        print("-" * 85)
        for user in users:
            print(f"{user[0]:<25} {user[1]:<20} {user[2]:<20} {user[3]:<15}")
    else:
        print(f"No users found matching '{search_term}'.")
    
    conn.close()

def change_password():
    """Change a user's password"""
    identifier = input("Enter the full name or username of the user to change password: ")
    
    try:
        conn = sqlite3.connect('loginusers.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT full_name, user_name FROM USERS WHERE full_name = ? OR user_name = ?', (identifier, identifier))
        user = cursor.fetchone()
        
        if user is None:
            print(f"No user found with the name or username '{identifier}'.")
            conn.close()
            return
        
        new_password = input(f"Enter new password for '{user[0]}': ")
        
        # Update the password
        cursor.execute('''
            UPDATE USERS 
            SET password = ?
            WHERE full_name = ?
        ''', (new_password, user[0]))
        
        conn.commit()
        conn.close()
        
        print(f"Password for user '{user[0]}' updated successfully.")
        
    except Exception as e:
        print(f"Error changing password: {e}")

def main():
    """Main function to run the application"""
    create_database()
    
    while True:
        print("\n=== Users Database Management ===")
        print("1. Add new user")
        print("2. View all users")
        print("3. Search user")
        print("4. Update user information")
        print("5. Delete user")
        print("6. Change password")
        print("7. Exit")
        
        choice = input("Enter your choice (1-7): ")
        
        if choice == '1':
            add_user()
        elif choice == '2':
            view_users()
        elif choice == '3':
            search_user()
        elif choice == '4':
            update_user()
        elif choice == '5':
            delete_user()
        elif choice == '6':
            change_password()
        elif choice == '7':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 