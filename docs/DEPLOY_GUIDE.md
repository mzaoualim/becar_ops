# Deploy guide (GitHub + Streamlit Community Cloud)

## 1) Create a GitHub repository

1. Create a new GitHub repo (public or private).
2. Upload all files from this folder.
3. **Do not commit** `.streamlit/secrets.toml`.

## 2) Deploy on Streamlit Community Cloud

1. Go to Streamlit Community Cloud and create a new app.
2. Select your GitHub repo and branch.
3. Set the main file to `app.py`.

### Password (required)

In the Streamlit Cloud app settings:

- Open **Advanced settings → Secrets**
- Paste:

```toml
[auth]
password = "YOUR_STRONG_PASSWORD"
```

(Alternatively, you can set an env var `APP_PASSWORD` locally.)

## 3) Share the demo link

- Share the URL in your email/cover letter.
- **Do not** publish the password publicly; share it on request.

## Security note

This is a simple password gate for a portfolio demo (not a full authentication system).
Do not host sensitive or personal data.
