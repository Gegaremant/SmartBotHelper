# Mock for tasks.py
def phone_exec(command):
    print(f"[tasks.py mock] Executing command on phone: {command}")

def click(x, y):
    print(f"[tasks.py mock] Clicking at {x}, {y}")

def speak(text):
    print(f"[tasks.py mock] Speaking: {text}")
