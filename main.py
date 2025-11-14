from app import app

# Render indítási pontja
if __name__ == "__main__":
    # Render NEM szereti a debug módot → kapcsold ki
    app.run(host="0.0.0.0", port=10000)
