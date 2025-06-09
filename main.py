from fastapi import FastAPI
from fastapi import HTTPException
from pymysql import cursors, connect, Error as mysqlError
from fastapi.responses import HTMLResponse
app = FastAPI()


def establish_db_connection():
    try:
        connection = connect(
            host='192.168.0.7',
            user='KitchenTrack',
            password='passwd',
            database='KitchenTrack',
            cursorclass=cursors.DictCursor
        )
        print("Connection successful!")
        return connection
    except mysqlError as e:
        print(f"Error connecting to MySQL: {e}")
        HTTPException(201, "No DB connection available")
        return None


def check_db_connection(connection):
    try:
        connection.ping(reconnect=True)  # Attempt to reconnect if connection is lost
        print("Connection is still active and healthy.")
        return True
    except mysqlError as e:
        print(f"Connection lost or unhealthy: {e}")
        return False


db = establish_db_connection()

try:
    with db.cursor() as cursor:
        sql = """
              CREATE TABLE IF NOT EXISTS meals
              (
                  id          INT AUTO_INCREMENT PRIMARY KEY,
                  dish        VARCHAR(255) NOT NULL,
                  calories    INT,
                  plate_types VARCHAR(255),
                  plate       VARCHAR(255),
                  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
              );
              """
        cursor.execute(sql)
        db.commit()
except mysqlError as e:
    print(f"Error creating cursor or executing query: {e}")


def execute_sql(sql: str):
    try:
        with db.cursor() as cursor:
            cursor.execute(sql)
            db.commit()
    except mysqlError as e:
        print(f"Error creating cursor or executing query: {e}")
        return cursor
    return cursor


@app.post("/meal/{dish_name}/")
def post_meal(dish_name: str,
              calories: int = None,
              plate_type: str = "plate",
              plates: int = 0,
              kcal_per_hundert: int = 0,
              grams_eaten: int = 0):
    """
        Calories in kcal
        """
    dish_name = dish_name.lower().replace(" ", "_")
    if not calories:
        calories = grams_eaten * kcal_per_hundert


    execute_sql(f"""
            INSERT INTO meals (dish, calories , plate_types, plate)
            VALUES ('{dish_name}', '{int(calories)}','{plate_type}', '{plates}');
            """)


@app.get("/meal/{dish_name}/")
def get_dish_data(dish_name: str):
    dish_name = dish_name.lower().replace(" ", "_")
    out = execute_sql(f"""
                SELECT dish, calories, plate_types
                FROM meals
                WHERE dish = '{dish_name}'
                  AND calories IS NOT NULL
                  AND calories > 0
                  AND plate_types IS NOT NULL
                  AND plate_types != ''
                GROUP BY dish, calories, plate_types
                ORDER BY COUNT(*) DESC
                LIMIT 1;
                """)
    data = out.fetchall()
    print(data)
    if data:
        return data[0]
    else:
        HTTPException(404, f"No meals titled {dish_name}")
        return False


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
