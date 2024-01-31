import os
extensions = ('.txt', '.py', '.db', '.css', '.js', '.html', '.ini', '.md')                                    #extinctions want to search
exclude_directories = set(['venv'])    #directory (only names) want to exclude
for dname, dirs, files in os.walk('.'):  #this loop though directies recursively 
    dirs[:] = [d for d in dirs if d not in exclude_directories] # exclude directory if in exclude list 
    for fname in files:
        if(fname.lower().endswith(extensions)): #check for extension 
           fpath = os.path.join(dname, fname)   #this generate full directory path for file
           print(fpath)