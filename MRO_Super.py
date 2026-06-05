class numbers:
    def __init__(self, num1, num2):
        self.num1 = num1
        self.num2 = num2

    def __str__(self):
        return f"Number: {self.num1}, {self.num2}"
    
    def __len__(self):
        return len(str(self.num1) + str(self.num2))

    def __repr__(self):
        return f"numbers({self.num1}, {self.num2})"

    def __eq__(self, other):
        if isinstance(other, numbers):
            return self.num1 == other.num1 and self.num2 == other.num2
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, numbers):
            return numbers(self.num1 + other.num1, self.num2 + other.num2)
        return NotImplemented
    
    def __sub__(self, other):
        if isinstance(other, numbers):
            return numbers(self.num1 - other.num1, self.num2 - other.num2)
        return NotImplemented


# Think of MRO (Method Resolution Order) like a treasure hunt. When you call a method, Python looks at the object.
#  If it doesn't find it there, it checks the parent class, then the grandparent, and so on.
#  MRO is the specific list of instructions telling Python which "room" to search next.



# The Technical Part
#  When you have complex inheritance, super() does not just call "the parent." It calls the next class in the MRO chain. 
# If you have a class that inherits from multiple parents, this prevents calling the same method twice!


class SimplifyNumber(numbers):
    def __init__(self, num1, num2):
        # Call parent constructor using super() 
        super().__init__(num1, num2)
        
        # Simplify by dividing both numbers by their GCD
        from math import gcd
        common_divisor = gcd(self.num1, self.num2)
        self.simplified_num1 = self.num1 // common_divisor
        self.simplified_num2 = self.num2 // common_divisor
    
    def __str__(self):
        return f"SimplifyNumber: {self.simplified_num1}/{self.simplified_num2} (original: {self.num1}, {self.num2})"
    
    def __repr__(self):
        return f"SimplifyNumber({self.num1}, {self.num2})"
    
    def get_simplified(self):
        return (self.simplified_num1, self.simplified_num2)

if __name__ == "__main__":
    # Using SimplifyNumber
    simple = SimplifyNumber(6, 8)
    print(simple)  # SimplifyNumber: 3/4 (original: 6, 8)
    print(simple.get_simplified())  #