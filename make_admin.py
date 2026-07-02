import os
from extensions import db
from models import UserModel

def main():
    email = 'vedicagrawalmva@gmail.com'
    session = db.session
    try:
        user = session.query(UserModel).filter_by(email=email).first()
        if user:
            user.is_admin = True
            session.commit()
            print(f"SUCCESS: Granted admin privileges to {email}")
        else:
            print(f"ERROR: User with email {email} not found. Please sign up first.")
    except Exception as e:
        print(f"EXCEPTION: {e}")
    finally:
        db.remove_session()

if __name__ == "__main__":
    main()
