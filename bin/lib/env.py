import os
import sys
import json

class Env:
    
    def __init__(self, args, create):
        self.verbose = args.verbose
        self.project_file = self.find_file(".tgfx", os.getcwd())
        
        if self.project_file == "" and args.func != create:
            print("Project file not found, exiting")
            sys.exit(1)
            
        with open(self.project_file) as file:
            data = json.load(file)
            
        for value in data:
            setattr(self, value, data[value])
            
    def find_file(self, filename, directory):
        if directory == "/":
            return ""
        else:
            if filename in os.listdir(directory):
                return os.path.join(directory, filename)
            else:
                return self.find_file(filename, os.path.abspath(os.path.join(directory, os.pardir)))