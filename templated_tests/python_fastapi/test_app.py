import pytest
from fastapi.testclient import TestClient
from app import *
from datetime import date
from helper import help

client = TestClient(app)

class Test:
    def __init__(self):
        self.test = 1
        self.lol = 2

    def foo(self, bar):
        self.lol = bar

def test_root():
    """
    Test the root endpoint by sending a GET request to "/" and checking the response status code and JSON body.
    """
    response = client.get("/")
    help()
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI application!"}

def test_current_date():
    """
    Test the current-date endpoint. This test references the `current_date` function.
    """
    response = client.get("/current-date")
    assert response.status_code == 200
    # We must compare the returned date with the current date to ensure accuracy.
    assert response.json() == {"date": date.today().isoformat()}


def test_add():
    """
    Test the add endpoint with positive numbers. This test references the `add` function.
    """
    response = client.get("/add/5/3")
    assert response.status_code == 200
    assert response.json() == {"result": 8}


def test_add_negative_numbers():
    """
    Test the add endpoint with negative numbers. This is a good use case for LSP
    "Go to References" to see the `add` function's usage.
    """
    response = client.get("/add/-10/5")
    assert response.status_code == 200
    assert response.json() == {"result": -5}


def test_subtract():
    """
    Test the subtract endpoint. This test references the `subtract` function.
    """
    response = client.get("/subtract/10/5")
    assert response.status_code == 200
    assert response.json() == {"result": 5}


def test_multiply():
    """
    Test the multiply endpoint. This test references the `multiply` function.
    """
    response = client.get("/multiply/4/5")
    assert response.status_code == 200
    assert response.json() == {"result": 20}


def test_divide_success():
    """
    Test the divide endpoint with valid input. This test references the `divide` function.
    """
    response = client.get("/divide/10/2")
    assert response.status_code == 200
    assert response.json() == {"result": 5.0}


def test_divide_by_zero():
    """
    Test the error handling for division by zero. This test case is important
    for "Go to Definition" on `HTTPException` and tracing the `divide` function's
    logic.
    """
    response = client.get("/divide/10/0")
    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot divide by zero"}


def test_square():
    """
    Test the square endpoint. This test references the `square` function.
    """
    response = client.get("/square/5")
    assert response.status_code == 200
    assert response.json() == {"result": 25}


def test_sqrt_positive():
    """
    Test the square root endpoint with a positive number. This test references the `sqrt` function.
    """
    response = client.get("/sqrt/25")
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(5.0)


def test_sqrt_negative():
    """
    Test the error handling for square root of a negative number. This provides another
    reference for `HTTPException` and the `sqrt` function.
    """
    response = client.get("/sqrt/-9")
    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot take square root of a negative number"}


def test_is_palindrome_true():
    """
    Test the palindrome checker with a valid palindrome.
    """
    response = client.get("/is-palindrome/racecar")
    assert response.status_code == 200
    assert response.json() == {"is_palindrome": True}


def test_is_palindrome_false():
    """
    Test the palindrome checker with a non-palindrome.
    """
    response = client.get("/is-palindrome/hello")
    assert response.status_code == 200
    assert response.json() == {"is_palindrome": False}


def test_days_until_new_year():
    """
    Test the days-until-new-year endpoint.
    """
    today = date.today()
    next_new_year = date(today.year + 1, 1, 1)
    delta = next_new_year - today
    response = client.get("/days-until-new-year")
    assert response.status_code == 200
    assert response.json() == {"days_until_new_year": delta.days}


def test_echo():
    """
    Test the echo endpoint with a simple message. This provides a direct reference to the `echo` function.
    """
    message_to_send = "Hello, World!"
    response = client.get(f"/echo/{message_to_send}")
    assert response.status_code == 200
    assert response.json() == {"message": message_to_send}

