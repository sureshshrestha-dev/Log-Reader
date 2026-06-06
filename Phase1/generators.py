# Generator Method:1
def log_generator(file_path):
    with open(file_path, 'r') as file:
        for line in file:
             yield line.strip()
             
# if __name__ == "__main__":
#     log_file_path = 'text.txt'  
#     for log_entry in log_generator(log_file_path):
#         print(log_entry)

# generator Method 2
# print(list(line.strip() for line in open('text.txt', 'r')))



def filter_error_logs(log_stream):
    for log_entry in log_stream:
        if 'ERROR' in log_entry:
            yield log_entry + ' need fix'

# How you will call it:

if __name__ == "__main__":
    logs = log_generator('text.txt')
    error_logs = filter_error_logs(logs)
    for error in error_logs:
        print(error)

