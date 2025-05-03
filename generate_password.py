import streamlit_authenticator as stauth

# Generate hashed password
hashed_passwords = stauth.Hasher(['admin123']).generate()
print(f"Hashed password: {hashed_passwords[0]}")
