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

if __name__ == "__main__":
    num1 = numbers(3, 4)
    num2 = numbers(5, 4)
    print(num1)  # Output: Number: 3, 4
    print(f"Length: {len(num1)}")  # Output: 7
    print(repr(num1))  # Output: numbers(3, 4)
    print(num1 == num2)  # Output: True