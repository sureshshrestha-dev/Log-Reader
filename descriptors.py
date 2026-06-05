# A descriptor is a class that controls how another class's attributes behave. 
# It's like a security guard or gatekeeper for your attribute.

class NumDescriptor:
    def __set__(self, instance, value):
        if not isinstance(value, int):
            raise ValueError("Value must be an integer")
        if value <= 0:
            raise ValueError("Value must be greater than 0")
        # Store the value in the instance's __dict__
        instance.__dict__[self.name] = value
    
    def __get__(self, instance, owner):
        """Called when reading the attribute"""
        if instance is None:
            return self
        return instance.__dict__.get(self.name, None)
    
    def __set_name__(self, owner, name):
        """Remember the attribute name"""
        self.name = name

class OperatorDescriptor:
    def __set__(self, instance, value):
        if not isinstance(value, str):
            raise ValueError("Value must be a string")
        if value.lower() not in ['add', 'subtract', 'multiply', 'divide']:
            raise ValueError("Value must be a valid operator")
        instance.__dict__[self.name] = value.lower()
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name, None)
    
    def __set_name__(self, owner, name):
        self.name = name

class Calculator:
    num1 = NumDescriptor()
    num2 = NumDescriptor()
    operator = OperatorDescriptor()
    
    def __init__(self, num1, num2, operator):
        self.num1 = num1
        self.num2 = num2
        self.operator = operator
    
    def _add(self):
        return self.num1 + self.num2
    
    def _subtract(self):
        return self.num1 - self.num2
    
    def _multiply(self):
        return self.num1 * self.num2
    
    def _divide(self):
        if self.num2 == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return self.num1 / self.num2
    
    def __str__(self):
        return f"Calculator with num1: {self.num1}, num2: {self.num2}, operator: {self.operator}"
    
    def __repr__(self):
        return f"Calculator({self.num1}, {self.num2}, '{self.operator}')"
    
    def calculate(self):
        operations = {
            'add': self._add,
            'subtract': self._subtract,
            'multiply': self._multiply,
            'divide': self._divide
        }
        return operations[self.operator]()

if __name__ == "__main__":
    calc = Calculator(10, 5, 'add')
    print(calc)  # Calculator with num1: 10, num2: 5, operator: add
    print(repr(calc))  # Calculator(10, 5, 'add')
    print(calc.calculate())  # 15
    
    # Test validation
    try:
        calc2 = Calculator(-5, 3, 'add')  # ValueError: Value must be greater than 0
    except ValueError as e:
        print(f"Validation works! {e}")
    
    try:
        calc3 = Calculator(10, 5, 'invalid')  # ValueError: Value must be a valid operator
    except ValueError as e:
        print(f"Operator validation works! {e}")