class MathOperations:
    def __init__(self, a, b, operation):
        self.a = a
        self.b = b
        self.operation = operation
        self.result = 0

    def __enter__(self):
        match self.operation:
            case "add":
                self.result = self.a + self.b
            case "subtract":
                self.result = self.a - self.b
            case "multiply":
                self.result = self.a * self.b
            case "divide":
                if self.b == 0:
                    raise ZeroDivisionError("Cannot divide by zero")
                self.result = self.a / self.b
            case _:
                raise ValueError(f"Unsupported operation: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.result = 0
        return False

if __name__ == "__main__":
    with MathOperations(10, 5, "add") as math_ops:
        print(f"Result: {math_ops.result}")  # 15
    
    with MathOperations(10, 5, "multiply") as math_ops:
        print(f"Result: {math_ops.result}")  # 50