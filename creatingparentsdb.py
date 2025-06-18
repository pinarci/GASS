import sqlite3

def create_database():
    """Create the database and PARENTS table"""
    conn = sqlite3.connect('parents.db')
    cursor = conn.cursor()
    
    # Create PARENTS table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PARENTS (
            full_name TEXT PRIMARY KEY,
            child_name TEXT NOT NULL,
            phone_number TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database 'parents.db' created successfully with PARENTS table.")

def add_parent():
    """Add a new parent to the database"""
    # Get parent information from user
    full_name = input("Enter parent's full name: ")
    child_name = input("Enter child's name: ")
    phone_number = input("Enter phone number: ")
    
    try:
        # Insert into database
        conn = sqlite3.connect('parents.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO PARENTS (full_name, child_name, phone_number)
            VALUES (?, ?, ?)
        ''', (full_name, child_name, phone_number))
        
        conn.commit()
        conn.close()
        
        print(f"Parent '{full_name}' added successfully.")
        
    except sqlite3.IntegrityError:
        print(f"Error: A parent with the name '{full_name}' already exists in the database.")
    except Exception as e:
        print(f"Error adding parent: {e}")

def view_parents():
    """View all parents in the database"""
    conn = sqlite3.connect('parents.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT full_name, child_name, phone_number FROM PARENTS')
    parents = cursor.fetchall()
    
    if parents:
        print("\nParents in database:")
        print("-" * 70)
        print(f"{'Parent Name':<25} {'Child Name':<25} {'Phone Number':<15}")
        print("-" * 70)
        for parent in parents:
            print(f"{parent[0]:<25} {parent[1]:<25} {parent[2]:<15}")
    else:
        print("No parents found in the database.")
    
    conn.close()

def delete_parent():
    """Delete a parent from the database"""
    full_name = input("Enter the full name of the parent to delete: ")
    
    try:
        conn = sqlite3.connect('parents.db')
        cursor = conn.cursor()
        
        # Check if parent exists
        cursor.execute('SELECT full_name FROM PARENTS WHERE full_name = ?', (full_name,))
        if cursor.fetchone() is None:
            print(f"No parent found with the name '{full_name}'.")
            conn.close()
            return
        
        # Delete the parent
        cursor.execute('DELETE FROM PARENTS WHERE full_name = ?', (full_name,))
        conn.commit()
        conn.close()
        
        print(f"Parent '{full_name}' deleted successfully.")
        
    except Exception as e:
        print(f"Error deleting parent: {e}")

def update_parent():
    """Update parent information"""
    full_name = input("Enter the full name of the parent to update: ")
    
    try:
        conn = sqlite3.connect('parents.db')
        cursor = conn.cursor()
        
        # Check if parent exists
        cursor.execute('SELECT * FROM PARENTS WHERE full_name = ?', (full_name,))
        parent = cursor.fetchone()
        
        if parent is None:
            print(f"No parent found with the name '{full_name}'.")
            conn.close()
            return
        
        print(f"\nCurrent information for '{full_name}':")
        print(f"Child Name: {parent[1]}")
        print(f"Phone Number: {parent[2]}")
        
        print("\nEnter new information (press Enter to keep current value):")
        new_child_name = input(f"Child Name ({parent[1]}): ") or parent[1]
        new_phone_number = input(f"Phone Number ({parent[2]}): ") or parent[2]
        
        # Update the parent
        cursor.execute('''
            UPDATE PARENTS 
            SET child_name = ?, phone_number = ?
            WHERE full_name = ?
        ''', (new_child_name, new_phone_number, full_name))
        
        conn.commit()
        conn.close()
        
        print(f"Parent '{full_name}' updated successfully.")
        
    except Exception as e:
        print(f"Error updating parent: {e}")

def search_parent():
    """Search for a parent by name or child name"""
    search_term = input("Enter parent name or child name to search: ")
    
    conn = sqlite3.connect('parents.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT full_name, child_name, phone_number 
        FROM PARENTS 
        WHERE full_name LIKE ? OR child_name LIKE ?
    ''', (f'%{search_term}%', f'%{search_term}%'))
    
    parents = cursor.fetchall()
    
    if parents:
        print(f"\nSearch results for '{search_term}':")
        print("-" * 70)
        print(f"{'Parent Name':<25} {'Child Name':<25} {'Phone Number':<15}")
        print("-" * 70)
        for parent in parents:
            print(f"{parent[0]:<25} {parent[1]:<25} {parent[2]:<15}")
    else:
        print(f"No parents found matching '{search_term}'.")
    
    conn.close()

def main():
    """Main function to run the application"""
    create_database()
    
    while True:
        print("\n=== Parents Database Management ===")
        print("1. Add new parent")
        print("2. View all parents")
        print("3. Search parent")
        print("4. Update parent information")
        print("5. Delete parent")
        print("6. Exit")
        
        choice = input("Enter your choice (1-6): ")
        
        if choice == '1':
            add_parent()
        elif choice == '2':
            view_parents()
        elif choice == '3':
            search_parent()
        elif choice == '4':
            update_parent()
        elif choice == '5':
            delete_parent()
        elif choice == '6':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 