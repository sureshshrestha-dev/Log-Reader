class Parent:
    def __init__(self, name):
        print(f"Parent __init__ called")
        self.name = name
    
    def greet(self):
        return f"Hello from Parent, I'm {self.name}"

class Child(Parent):
    def __init__(self, name, age):
        print(f"Child __init__ called")
        super().__init__(name)  # Calls Parent.__init__
        self.age = age
    
    def greet(self):
        # Call parent's greet method first
        parent_greeting = super().greet()
        return f"{parent_greeting}. I'm {self.age} years old"

# Using the classes
child = Child("Alice", 10)
print(child.greet())

# Output:
# Child __init__ called
# Parent __init__ called
# Hello from Parent, I'm Alice. I'm 10 years old


class A:
    def method(self):
        print("A's method")

class B(A):
    def method(self):
        print("B's method")
        super().method()  # Calls A's method

class C(A):
    def method(self):
        print("C's method")
        super().method()  # Calls A's method

class D(B, C):
    def method(self):
        print("D's method")
        super().method()  # Calls B's method (then C, then A)

# Check MRO
print(D.__mro__)
# Output: (<class '__main__.D'>, <class '__main__.B'>, 
#          <class '__main__.C'>, <class '__main__.A'>, <class 'object'>)

d = D()
d.method()
# Output:
# D's method
# B's method
# C's method
# A's method