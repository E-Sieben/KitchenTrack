from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pymysql import cursors, connect, Error as MySQLError

app = FastAPI()

DB_CONFIG = {
    'host': '192.168.0.7',
    'user': 'KitchenTrack',
    'password': 'passwd',
    'database': 'KitchenTrack',
    'cursorclass': cursors.DictCursor
}

def on_startup():
    connection = None
    try:
        connection = connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            sql = """
            CREATE TABLE IF NOT EXISTS meals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                dish VARCHAR(255) NOT NULL,
                calories INT,
                plate_types VARCHAR(255),
                plate VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(sql)
        connection.commit()
    except MySQLError as e:
        print(f"Error during startup DB initialization: {e}")
    finally:
        if connection and connection.open:
            connection.close()
on_startup()

def get_db():
    connection = None
    try:
        connection = connect(**DB_CONFIG)
        yield connection
    except MySQLError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {e}"
        )
    finally:
        if connection and connection.open:
            connection.close()

@app.post("/meal/{dish_name}/")
def post_meal(
    dish_name: str,
    calories: int = None,
    plate_type: str = "plate",
    plates: int = 0,
    kcal_per_hundert: int = 0,
    grams_eaten: int = 0,
    db: connect = Depends(get_db)
):
    final_dish_name = dish_name.lower().replace(" ", "_")
    if calories is None:
        calories = grams_eaten * kcal_per_hundert

    sql = "INSERT INTO meals (dish, calories, plate_types, plate) VALUES (%s, %s, %s, %s);"
    try:
        with db.cursor() as cursor:
            cursor.execute(sql, (final_dish_name, int(calories), plate_type, str(plates)))
        db.commit()
        return {"status": "success", "dish_name": final_dish_name, "calories": calories}
    except MySQLError as e:
        raise HTTPException(status_code=500, detail=f"Database write error: {e}")

@app.get("/meal/{dish_name}/")
def get_dish_data(dish_name: str, db: connect = Depends(get_db)):
    final_dish_name = dish_name.lower().replace(" ", "_")
    sql = """
        SELECT dish, calories, plate_types
        FROM meals
        WHERE dish = %s
          AND calories IS NOT NULL AND calories > 0
          AND plate_types IS NOT NULL AND plate_types != ''
        GROUP BY dish, calories, plate_types
        ORDER BY COUNT(*) DESC
        LIMIT 1;
    """
    try:
        with db.cursor() as cursor:
            cursor.execute(sql, (final_dish_name,))
            data = cursor.fetchone()
        if data:
            return data
        else:
            raise HTTPException(status_code=404, detail=f"No meals titled '{dish_name}' found.")
    except MySQLError as e:
        raise HTTPException(status_code=500, detail=f"Database read error: {e}")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("index.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading index.html: {e}")

