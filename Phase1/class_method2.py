class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    @classmethod
    def baby(cls, name):
        """Create a baby (age 0)"""
        return cls(name, 0)
    
    @classmethod
    def teenager(cls, name):
        """Create a teenager (age 13)"""
        return cls(name, 13)
    
    @classmethod
    def senior(cls, name):
        """Create a senior (age 65)"""
        return cls(name, 65)
    
    def introduce(self):
        print(f"I'm {self.name}, age {self.age}")

# Creating people in different ways
person1 = Person("John", 25)           # Regular way
person2 = Person.baby("Timmy")          # Class method: baby
person3 = Person.teenager("Sarah")      # Class method: teenager
person4 = Person.senior("Grandpa")      # Class method: senior

person1.introduce()  # I'm John, age 25
person2.introduce()  # I'm Timmy, age 0
person3.introduce()  # I'm Sarah, age 13
person4.introduce()  # I'm Grandpa, age 65