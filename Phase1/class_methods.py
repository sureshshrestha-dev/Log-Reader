class Calculator:
    def __init__(self, start_value):
        self.value = start_value
    
    @classmethod
    def start_from_zero(cls):
        """Class method - creates calculator starting at 0"""
        return cls(0)  # cls() is same as Calculator()
    
    @classmethod
    def start_from_hundred(cls):
        """Class method - creates calculator starting at 100"""
        return cls(100)
    
    @classmethod
    def start_from_fifty(cls):
        """Class method - creates calculator starting at 50"""
        return cls(50)
    
    def add(self, num):
        self.value += num
        return self
    
    def subtract(self, num):
        self.value -= num
        return self

# Using regular constructor
calc1 = Calculator(10)
print(calc1.value)  # 10

# Using class methods (much clearer!)
calc2 = Calculator.start_from_zero()
print(calc2.value)  # 0

calc3 = Calculator.start_from_hundred()
print(calc3.value)  # 100

calc4 = Calculator.start_from_fifty()
print(calc4.value)  # 50