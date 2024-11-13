from typing import Optional
import os
from dotenv import load_dotenv
import mysql.connector
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from mysql.connector import errorcode
import jwt

# Load environment variables
load_dotenv()

# Initialize the todoapi app
app = FastAPI()

# Define the allowed origins for CORS
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database connection function
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            user=os.environ['MYSQL_USER'],
            password=os.environ['MYSQL_PASSWORD'],
            host=os.environ['MYSQL_HOST'].split(':')[0],  # Remove the port number from host
            port=3306,  # Specify port separately
            database=os.environ['MYSQL_DB'],
        )
        return connection
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid database credentials"
            )
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database does not exist"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(err)
            )

# Define the authentication middleware
async def authenticate(request: Request):
    try:
        auth_header = request.headers.get('authorization')
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authorization header"
            )
            
        token = auth_header.replace("Bearer ", "")
        try:
            payload = jwt.decode(token, os.environ['SECRET_KEY'], algorithms=['HS256'])
            return payload
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

# Define the login endpoint
@app.get("/login")
async def login(voter_id: str, password: str):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT role FROM voters WHERE voter_id = %s AND password = %s", (voter_id, password,))
        role = cursor.fetchone()
        
        if role:
            # Generate token only if credentials are valid
            token = jwt.encode(
                {'voter_id': voter_id, 'role': role[0]}, 
                os.environ['SECRET_KEY'], 
                algorithm='HS256'
            )
            return {'token': token, 'role': role[0]}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid voter id or password"
            )
    except mysql.connector.Error as err:
        print(err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    finally:
        cursor.close()
        connection.close()