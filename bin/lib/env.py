import os, sys

class Env:
    
    def __init__(self, args, create):
        self.verbose = args.verbose
        self.project_file = self.find_file(".tgfx", os.getcwd())
        
        if self.project_file == "" and args.func != create:
            print("Project file not found, exiting")
            sys.exit(1)
    
    def find_file(self, filename, directory):
        if directory == "/":
            return ""
        else:
            if filename in os.listdir(directory):
                return os.path.join(directory, filename)
            else:
                return self.find_file(filename, os.path.abspath(os.path.join(directory, os.pardir)))