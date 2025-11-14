from app import app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
@app.before_request
def create_tables():
    if not hasattr(app, 'tables_created'):
        db.create_all()
        app.tables_created = True
